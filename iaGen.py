import torch
import torch.nn as nn
import torch.nn.functional as F


class generatorNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.ConvTranspose2d(100, 512, 4, 1, 0, bias=False)
        self.conv2 = nn.ConvTranspose2d(512, 256, 4, 2, 1, bias=False)
        self.conv3 = nn.ConvTranspose2d(256, 128, 4, 2, 1, bias=False)
        self.conv4 = nn.ConvTranspose2d(128,  64, 4, 2, 1, bias=False)
        self.conv5 = nn.ConvTranspose2d( 64,   3, 4, 2, 1, bias=False)

        self.bn1 = nn.BatchNorm2d(512)
        self.bn2 = nn.BatchNorm2d(256)
        self.bn3 = nn.BatchNorm2d(128)
        self.bn4 = nn.BatchNorm2d( 64)

    def forward(self, x):
        x = F.relu(self.bn1(self.conv1(x)))
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.relu(self.bn3(self.conv3(x)))
        x = F.relu(self.bn4(self.conv4(x)))
        return torch.tanh(self.conv5(x))


def setup_iaGen():
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    gnet = generatorNet().to(device)

    async def generate(ia_type):
        import os
        model_path = f"models/gnet_{ia_type}.pth"

        if not os.path.exists(model_path):
            return None

        gnet.load_state_dict(torch.load(model_path, map_location=device))
        gnet.eval()

        with torch.no_grad():
            noise = torch.randn(1, 100, 1, 1).to(device)
            fake_image = gnet(noise)

        fake_image = (fake_image + 1) / 2
        fake_image = fake_image.squeeze(0).cpu()

        import io
        from torchvision.utils import save_image
        buffer = io.BytesIO()
        save_image(fake_image, buffer, format="PNG")
        buffer.seek(0)

        return buffer

    return {"generate": generate}