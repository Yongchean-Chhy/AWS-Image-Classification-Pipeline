import argparse
import torch
import torch.nn.functional as F
from torchvision import models
from PIL import Image

def predict_dog_breed(image_path, top_k=3):
    # 1. Load pre-trained ResNet-50 and extract Built-in Labels
    weights = models.ResNet50_Weights.DEFAULT
    labels = weights.meta["categories"]  # Official ImageNet-1k labels
    
    model = models.resnet50(weights=weights)
    model.eval()

    # 2. Use official model preprocessing
    preprocess = weights.transforms()

    # 3. Load image
    try:
        img = Image.open(image_path).convert("RGB")
    except Exception as e:
        print(f"Error opening image: {e}")
        return

    img_tensor = preprocess(img).unsqueeze(0)

    # 4. Inference
    with torch.no_grad():
        output = model(img_tensor)
        probabilities = F.softmax(output[0], dim=0)

    # 5. Get top-k results
    top_probs, top_indices = torch.topk(probabilities, top_k)

    # 6. Print Output
    print(f"\nTarget Image: {image_path}")
    print("=" * 45)
    print(f"{'Rank':<6}{'Predicted Breed / Class':<28}{'Confidence':<10}")
    print("-" * 45)

    for i in range(top_k):
        idx = top_indices[i].item()
        prob = top_probs[i].item() * 100
        label = labels[idx]
        print(f"{i+1:<6}{label:<28}{prob:>6.2f}%")
    print("=" * 45)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Predict Dog Breed from Image CLI")
    parser.add_argument("--image", required=True, help="Path to input image file")
    parser.add_argument("--top_k", type=int, default=3, help="Number of top predictions to display")
    
    args = parser.parse_args()
    predict_dog_breed(args.image, args.top_k)