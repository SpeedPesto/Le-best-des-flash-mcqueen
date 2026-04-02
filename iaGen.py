import asyncio
import json

import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as T
from torchvision import datasets
from torch.utils.data import DataLoader, TensorDataset
from torch.amp import autocast
from torch.cuda.amp import GradScaler
import os

class discriminatorNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(  3,  64, 4, 2, 1, bias=False)
        self.conv2 = nn.Conv2d( 64, 128, 4, 2, 1, bias=False)
        self.conv3 = nn.Conv2d(128, 256, 4, 2, 1, bias=False)
        self.conv4 = nn.Conv2d(256, 512, 4, 2, 1, bias=False)
        self.conv5 = nn.Conv2d(512,   1, 4, 1, 0, bias=False)

        self.bn2 = nn.BatchNorm2d(128)
        self.bn3 = nn.BatchNorm2d(256)
        self.bn4 = nn.BatchNorm2d(512)

    def forward(self, x):
        x = F.leaky_relu(self.conv1(x), 0.2)
        x = F.leaky_relu(self.bn2(self.conv2(x)), 0.2)
        x = F.leaky_relu(self.bn3(self.conv3(x)), 0.2)
        x = F.leaky_relu(self.bn4(self.conv4(x)), 0.2)
        return self.conv5(x).view(-1, 1)

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
    state = {"is_training": False}
    batchsize = 256

    scaler_d = GradScaler()
    scaler_g = GradScaler()

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(device)

    dnet = discriminatorNet().to(device)
    gnet = generatorNet().to(device)

    lossfun = nn.BCEWithLogitsLoss()

    d_optimizer = torch.optim.Adam(dnet.parameters(), lr=0.0002, betas=(0.5, 0.999))
    g_optimizer = torch.optim.Adam(gnet.parameters(), lr=0.0002, betas=(0.5, 0.999))

    losses = []

    dnet.train()
    gnet.train()

    transform = T.Compose([
        T.Resize(64),
        T.CenterCrop(64),
        T.ToTensor(),
        T.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
    ])

    def preload_dataset(dataset):
        loader = DataLoader(dataset, batch_size=256, num_workers=4, pin_memory=True)
        all_images = []
        for imgs, _ in loader:
            all_images.append(imgs)
        print("images loaded")
        return TensorDataset(torch.cat(all_images))

    async def training(ia_type, ia_default_stats, on_epoch=None):
        loop = asyncio.get_event_loop()
        state["is_training"] = True
        epochi = 0

        if os.path.exists(f"models/dnet_{ia_type}.pth") and os.path.exists(f"models/gnet_{ia_type}.pth"):
            dnet.load_state_dict(torch.load(f"models/dnet_{ia_type}.pth", map_location=device))
            gnet.load_state_dict(torch.load(f"models/gnet_{ia_type}.pth", map_location=device))
            print(f"Models de {ia_type} chargés avec succès !")
        else:
            print(f"Aucun modèle de {ia_type} trouvé")

        chemin_images = f'DataSets/{ia_type}'
        dataset = datasets.ImageFolder(root=chemin_images, transform=transform)
        preloaded = preload_dataset(dataset)
        data_loader = DataLoader(preloaded, batch_size=batchsize, shuffle=True, drop_last=True, num_workers=0, pin_memory=True)

        def train_step():
            nonlocal epochi
            while state["is_training"]:
                for (data,) in data_loader:
                    if not state["is_training"]:
                        break

                    data = data.to(device)
                    real_labels = torch.ones(batchsize, 1).to(device)
                    fake_labels = torch.zeros(batchsize, 1).to(device)

                    with autocast(device_type='cuda'):
                        pred_real = dnet(data)
                        d_loss_real = lossfun(pred_real, real_labels)
                        fake_images = gnet(torch.randn(batchsize, 100, 1, 1).to(device))
                        pred_fake = dnet(fake_images.detach())
                        d_loss_fake = lossfun(pred_fake, fake_labels)
                        d_loss = d_loss_real + d_loss_fake

                    d_optimizer.zero_grad(set_to_none=True)
                    scaler_d.scale(d_loss).backward()
                    scaler_d.step(d_optimizer)
                    scaler_d.update()

                    with autocast(device_type='cuda'):
                        fake_images = gnet(torch.randn(batchsize, 100, 1, 1).to(device))
                        pred_fake = dnet(fake_images)
                        g_loss = lossfun(pred_fake, real_labels)

                    g_optimizer.zero_grad(set_to_none=True)
                    scaler_g.scale(g_loss).backward()
                    scaler_g.step(g_optimizer)
                    scaler_g.update()

                    losses.append([d_loss.item(), g_loss.item()])

                epochi += 1
                if epochi % 5 == 0:
                    if on_epoch:
                        img = generate_sync()
                        asyncio.run_coroutine_threadsafe(on_epoch(epochi, img), loop)
                if epochi % 10 == 0:
                    ia_data = load_ia()
                    get_type_data(ia_data, ia_type, ia_default_stats)["epoch"] += 10
                    save_ia(ia_data)
                if epochi % 15 == 0:
                    asyncio.run_coroutine_threadsafe(save(ia_type), loop)
                    print("ia sauvegardé par sécurité")
                print(f'Epoch {epochi}')

        await asyncio.to_thread(train_step)

    def load_ia():
        if os.path.exists("ia.json"):
            with open("ia.json", "r") as f:
                return json.load(f)
        else:
            return {}

    def save_ia(ia):
        with open("ia.json", "w") as f:
            json.dump(ia, f, indent=4)

    def get_type_data(data, ia_type, ia_default_stats):
        if ia_type not in data:
            data[ia_type] = ia_default_stats.copy()
        return data[ia_type]

    async def stop_training():
        state["is_training"] = False

    async def save(ia_type):
        path = "models/"
        os.makedirs(path, exist_ok=True)

        torch.save(gnet.state_dict(), path + f"gnet_{ia_type}.pth")
        torch.save(dnet.state_dict(), path + f"dnet_{ia_type}.pth")

        state["is_training"] = False
        print("Modèles sauvegardés !")

    async def generate():
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

        gnet.train()
        return buffer

    def generate_sync():
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
        gnet.train()
        return buffer

    return {"training": training, "stop_training": stop_training, "save": save, "generate": generate}