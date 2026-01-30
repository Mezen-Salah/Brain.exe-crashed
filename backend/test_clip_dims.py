import clip
import torch

model, _ = clip.load('ViT-B/32', device='cpu')
text = clip.tokenize(['test'])
with torch.no_grad():
    features = model.encode_text(text)
print(f'Shape: {features.shape}')
print(f'Dimensions: {features.shape[1]}')
