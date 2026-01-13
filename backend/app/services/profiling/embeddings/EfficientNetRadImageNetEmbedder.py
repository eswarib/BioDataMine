# =========================
# profiling/embeddings/efficientnet_embedder.py
# =========================

import timm


class EfficientNetRadImageNetEmbedder(BaseEmbedder):
    def __init__(self, device: str = "cuda"):
        self.device = device
        self.model = self.load_model()
        self.transform = transforms.Compose([
            transforms.Resize((300, 300)),
            transforms.ToTensor(),
        ])

    def load_model(self):
        model = timm.create_model(
            "efficientnet_b3",
            pretrained=True,
            num_classes=0  # removes classifier head
        )
        model.eval()
        model.to(self.device)
        return model

    def preprocess(self, image):
        if image.mode != "RGB":
            image = image.convert("RGB")
        return self.transform(image).unsqueeze(0).to(self.device)

    @torch.no_grad()
    def embed(self, image):
        x = self.preprocess(image)
        features = self.model(x)
        return features.squeeze(0).cpu().numpy()

