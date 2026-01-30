"""
Agent 4: Explainer
Generates LLM-based explanations with fact verification and trust scoring
"""
import re
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from google import genai
from google.genai import types

from models.state import AgentState
from models.schemas import Product
from core.config import settings
from core.redis_client import redis_manager

logger = logging.getLogger(__name__)


class ExplainerAgent:
    """
    Agent 4: Explainer
    
    Generates human-readable explanations for top recommendations using LLM.
    Verifies factual accuracy and calculates trust scores.
    """
    
    def __init__(self):
        """Initialize the Explainer Agent with Gemini LLM"""
        self.max_regeneration_attempts = 2
        self.trust_threshold = 70.0  # Minimum trust score
        
        # Configure Gemini
        if settings.google_api_key:
            self.client = genai.Client(api_key=settings.google_api_key)
            self.model_name = settings.llm_model
            logger.info(f"Gemini LLM initialized: {settings.llm_model}")
        else:
            self.client = None
            self.model_name = None
            logger.warning("Google API key not configured - Agent 4 will use fallback explanations")
    
    def execute(self, state: AgentState) -> AgentState:
        """
        Main execution method for Agent 4
        
        Args:
            state: Current agent state with recommendations
            
        Returns:
            Updated state with enhanced explanations and trust scores
        """
        start_time = time.time()
        logger.info("Agent 4: Starting explanation generation")
        
        recommendations = state.get('final_recommendations', [])
        
        if not recommendations:
            logger.warning("Agent 4: No recommendations to explain")
            state['agent4_execution_time'] = int((time.time() - start_time) * 1000)
            return state
        
        # Process top 3 recommendations with detailed explanations
        top_recommendations = recommendations[:3]
        
        for i, rec in enumerate(top_recommendations):
            try:
                # Gather context
                context = self._gather_context(rec, state)
                
                # Generate explanation with LLM
                if self.client:
                    explanation, trust_score = self._generate_llm_explanation(
                        rec, context, state
                    )
                else:
                    # Fallback to template-based explanation
                    explanation = rec.get('explanation', '')
                    trust_score = 100.0  # Trust template-based explanations
                
                # Update recommendation
                rec['detailed_explanation'] = explanation
                rec['trust_score'] = trust_score
                rec['verified'] = trust_score >= self.trust_threshold
                
                logger.info(
                    f"Generated explanation for #{i+1} {rec['product'].name} "
                    f"(trust: {trust_score:.1f}%)"
                )
                
            except Exception as e:
                logger.error(f"Failed to explain recommendation #{i+1}: {e}")
                rec['detailed_explanation'] = rec.get('explanation', 'No explanation available')
                rec['trust_score'] = 0.0
                rec['verified'] = False
        
        # Add execution time
        execution_time = int((time.time() - start_time) * 1000)
        state['agent4_execution_time'] = execution_time
        state['explainer_time_ms'] = execution_time
        
        logger.info(f"Agent 4 complete: Explained {len(top_recommendations)} recommendations in {execution_time}ms")
        
        return state
    
    def _gather_context(self, recommendation: Dict[str, Any], state: AgentState) -> Dict[str, Any]:
        """
        Gather context for explanation generation
        
        Args:
            recommendation: Single recommendation dict
            state: Current agent state
            
        Returns:
            Context dictionary with all relevant information
        """
        product = recommendation['product']
        scores = recommendation.get('scores', {})
        affordability = recommendation.get('affordability', {})
        user = state.get('user_profile')
        
        # Get Thompson Sampling stats
        thompson_params = {'alpha': 1.0, 'beta': 1.0, 'total_views': 0, 'total_clicks': 0}
        try:
            thompson_params = redis_manager.get_thompson_params(product.product_id)
        except Exception as e:
            logger.warning(f"Could not get Thompson params: {e}")
        
        # Extract financial rules applied
        financial_rules = []
        if 'financial_rules_applied' in affordability:
            financial_rules = affordability.get('financial_rules_applied', [])
        
        context = {
            # Product details
            'product_name': product.name,
            'product_price': product.price,
            'product_category': product.category,
            'product_rating': product.rating,
            'product_reviews': product.num_reviews,
            'financing_available': product.financing_available,
            
            # Scoring details
            'thompson_score': scores.get('thompson', 0),
            'collaborative_score': scores.get('collaborative', 0),
            'ragas_score': scores.get('ragas', 0),
            'financial_score': scores.get('financial', 0),
            'final_score': recommendation.get('final_score', 0),
            
            # Affordability
            'can_afford_cash': affordability.get('can_afford_cash', False),
            'can_afford_financing': affordability.get('can_afford_financing', False),
            'risk_level': str(affordability.get('risk_level', 'UNKNOWN')),
            'disposable_income': affordability.get('disposable_income', 0),
            
            # User context
            'monthly_income': user.monthly_income if user else 0,
            'credit_score': user.credit_score if user else 0,
            'query': state.get('query', ''),
            
            # Social proof
            'total_views': thompson_params.get('total_views', 0),
            'total_clicks': thompson_params.get('total_clicks', 0),
            'engagement_rate': (
                thompson_params.get('total_clicks', 0) / max(thompson_params.get('total_views', 1), 1)
            ) * 100,
            
            # Financial rules
            'financial_rules': financial_rules,
        }
        
        return context
    
    def _generate_llm_explanation(
        self, 
        recommendation: Dict[str, Any], 
        context: Dict[str, Any],
        state: AgentState
    ) -> Tuple[str, float]:
        """
        Generate explanation using Gemini LLM with verification
        
        Args:
            recommendation: Single recommendation
            context: Context dict
            state: Agent state
            
        Returns:
            Tuple of (explanation_text, trust_score)
        """
        attempts = 0
        best_explanation = ""
        best_trust_score = 0.0
        
        while attempts <= self.max_regeneration_attempts:
            try:
                # Build prompt
                prompt = self._build_prompt(context)
                
                # Call Gemini
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=settings.llm_temperature,
                        max_output_tokens=settings.llm_max_tokens,
                    )
                )
                
                explanation = response.text.strip()
                
                # Verify facts
                trust_score = self._verify_explanation(explanation, context)
                
                # Track best attempt
                if trust_score > best_trust_score:
                    best_explanation = explanation
                    best_trust_score = trust_score
                
                # If trust is high enough, accept
                if trust_score >= self.trust_threshold:
                    logger.info(f"Explanation verified with trust {trust_score:.1f}% on attempt {attempts + 1}")
                    return explanation, trust_score
                
                logger.warning(
                    f"Low trust score {trust_score:.1f}% on attempt {attempts + 1}, "
                    f"regenerating..."
                )
                
            except Exception as e:
                logger.error(f"LLM generation failed on attempt {attempts + 1}: {e}")
            
            attempts += 1
        
        # Return best attempt even if below threshold
        logger.warning(
            f"Max regeneration attempts reached. Best trust: {best_trust_score:.1f}%"
        )
        return best_explanation, best_trust_score
    
    def _build_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build structured prompt for Gemini
        
        Args:
            context: Context dictionary
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are a financial advisor helping a customer understand why a product is recommended.

Product: {context['product_name']}
Price: ${context['product_price']:.2f}
Category: {context['product_category']}
Rating: {context['product_rating']}/5 ({context['product_reviews']} reviews)

User Context:
- Monthly Income: ${context['monthly_income']:.2f}
- Credit Score: {context['credit_score']}
- Search Query: "{context['query']}"

Recommendation Scores:
- Overall Match: {context['final_score']:.1f}/100
- Popularity: {context['thompson_score']:.1f}/100
- Relevancy: {context['ragas_score']:.1f}/100
- Financial Fit: {context['financial_score']:.1f}/100

Affordability:
- Can afford with cash: {context['can_afford_cash']}
- Can afford with financing: {context['can_afford_financing']}
- Risk Level: {context['risk_level']}
- Disposable Income: ${context['disposable_income']:.2f}

Social Proof:
- Product Views: {context['total_views']}
- Engagement Rate: {context['engagement_rate']:.1f}%

Generate a concise, helpful explanation (3-4 sentences) explaining:
1. WHY this product is recommended
2. HOW it fits their financial situation
3. WHAT makes it a smart choice

Be specific with numbers. Be honest about risks. Focus on value.

Explanation:"""
        
        return prompt
    
    def _verify_explanation(self, explanation: str, context: Dict[str, Any]) -> float:
        """
        Verify factual accuracy of LLM explanation
        
        Args:
            explanation: Generated explanation text
            context: Ground truth context
            
        Returns:
            Trust score 0-100
        """
        trust_score = 100.0  # Start with perfect score
        
        # Extract numbers from explanation
        numbers_in_text = self._extract_numbers(explanation)
        
        # Verify product price
        if any(abs(num - context['product_price']) < 1.0 for num in numbers_in_text):
            trust_score += 0  # Correct price mentioned
        elif str(context['product_price']) in explanation or f"${context['product_price']:.0f}" in explanation:
            trust_score += 0  # Price mentioned correctly
        else:
            # Check if price is hallucinated (wrong price mentioned)
            price_mentions = re.findall(r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', explanation)
            if price_mentions:
                for price_str in price_mentions:
                    mentioned_price = float(price_str.replace(',', ''))
                    if abs(mentioned_price - context['product_price']) > 50:
                        trust_score -= 15  # Wrong price is serious error
        
        # Verify rating
        rating_pattern = r'(\d+(?:\.\d+)?)\s*(?:/\s*5|out of 5|stars?)'
        rating_matches = re.findall(rating_pattern, explanation.lower())
        if rating_matches:
            for rating_str in rating_matches:
                mentioned_rating = float(rating_str)
                if abs(mentioned_rating - context['product_rating']) > 0.3:
                    trust_score -= 10  # Wrong rating
        
        # Verify income (if mentioned)
        if context['monthly_income'] > 0:
            income_close = any(
                abs(num - context['monthly_income']) < 100 
                for num in numbers_in_text
            )
            if not income_close and any(num > 1000 for num in numbers_in_text):
                # Large number mentioned that doesn't match income
                trust_score -= 5
        
        # Check for hallucinated affordability claims
        if not context['can_afford_cash'] and not context['can_afford_financing']:
            if any(phrase in explanation.lower() for phrase in ['easily afford', 'well within budget', 'very affordable']):
                trust_score -= 20  # Claimed affordable when it's not
        
        # Check risk level consistency
        risk_level = context['risk_level']
        if 'RISKY' in risk_level:
            if any(phrase in explanation.lower() for phrase in ['safe choice', 'low risk', 'no financial risk']):
                trust_score -= 15  # Claimed safe when risky
        
        # Verify scores (should be 0-100)
        score_numbers = re.findall(r'(\d+(?:\.\d+)?)\s*(?:/\s*100|%|\s+score)', explanation.lower())
        for score_str in score_numbers:
            score = float(score_str)
            if score > 100:
                trust_score -= 10  # Invalid score
        
        # Check for product name consistency
        product_name_lower = context['product_name'].lower()
        explanation_lower = explanation.lower()
        
        # Extract key words from product name
        product_keywords = set(product_name_lower.split())
        product_keywords.discard('the')
        product_keywords.discard('a')
        product_keywords.discard('an')
        
        # Check if at least some keywords are mentioned
        keywords_mentioned = sum(1 for kw in product_keywords if kw in explanation_lower)
        if keywords_mentioned == 0 and len(product_keywords) > 2:
            trust_score -= 10  # Product not properly referenced
        
        # Ensure trust score is in valid range
        trust_score = max(0.0, min(100.0, trust_score))
        
        return trust_score
    
    def _extract_numbers(self, text: str) -> List[float]:
        """
        Extract all numbers from text
        
        Args:
            text: Input text
            
        Returns:
            List of float numbers
        """
        # Match various number formats: 1234, 1,234, 1234.56, $1234.56, etc.
        number_pattern = r'\$?\s*(\d+(?:,\d{3})*(?:\.\d+)?)'
        matches = re.findall(number_pattern, text)
        
        numbers = []
        for match in matches:
            try:
                # Remove commas and convert to float
                num = float(match.replace(',', ''))
                numbers.append(num)
            except ValueError:
                continue
        
        return numbers


# Global instance
explainer_agent = ExplainerAgent()
