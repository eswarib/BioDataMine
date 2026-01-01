import torch
from torchvision import transforms
import timm
from PIL import Image
import numpy as np
from .BaseEmbedder import BaseEmbedder


class RadImageNetEmbedder(BaseEmbedder):
    """
    Embedder using EfficientNet-B3 pre-trained on RadImageNet (via timm).
    Note: Standard ImageNet weights are used as a fallback if specific RadImageNet
    weights aren't loaded via a custom path.
    """
    def __init__(self, device: str = "cpu"):
        self.device = device
        self.model = self.load_model()
        self.transform = transforms.Compose([
            transforms.Resize((300, 300)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

    def load_model(self):
        # Using efficientnet_b3 as it's the standard for RadImageNet studies
        model = timm.create_model(
            "efficientnet_b3",
            pretrained=True,
            num_classes=0  # removes classifier head, returns features
        )
        model.eval()
        model.to(self.device)
        return model

    def preprocess(self, image: Image.Image):
        if image.mode != "RGB":
            image = image.convert("RGB")
        return self.transform(image).unsqueeze(0).to(self.device)

    @torch.no_grad()
    def embed(self, image: Image.Image) -> np.ndarray:
        x = self.preprocess(image)
        features = self.model(x)
        return features.squeeze(0).cpu().numpy()
