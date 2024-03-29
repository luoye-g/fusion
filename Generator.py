import torch.nn.functional as F
from torch import nn
import torch

class DenseBlock(nn.Module):
    """
    DenseNet密连接
    """
    def __init__(self,channels,beta = 0.5):
        super(DenseBlock,self).__init__()
        self.beta = beta
        self.conv_module1 = nn.Sequential(
                nn.Conv2d(channels,channels,3,1,padding=1),
                nn.LeakyReLU(inplace=True)
                )
        self.conv_module2 = nn.Sequential(
                nn.Conv2d(channels,channels,3,1,padding=1),
                nn.LeakyReLU(inplace=True)
                )
        self.conv_module3 = nn.Sequential(
                nn.Conv2d(channels,channels,3,1,padding=1),
                nn.LeakyReLU(inplace=True)
                )
        self.conv_module4 = nn.Sequential(
                nn.Conv2d(channels,channels,3,1,padding=1),
                nn.LeakyReLU(inplace=True)
                )
        self.last_conv = nn.Conv2d(channels,channels,3,1,padding = 1) 
    def forward(self,x): #three layer
        module1_out = self.conv_module1(x)
        module1_out_temp = x+module1_out
        module2_out = self.conv_module2(module1_out_temp)
        module2_out_temp = x+module1_out_temp+module2_out
        module4_out_temp = x+module1_out_temp+module2_out_temp
        last_conv = self.last_conv(module4_out_temp)
        out = x + last_conv*self.beta
        return out


class Light(nn.Module):
    """
    Denseblock,Unet,大感受野
    融合
    """
    def __init__(self,in_c,out_c,residual_beta = 0.5):
        """
        in_c :输入的通道数
        out_c: 输出的通道数
        """
        super(Light,self).__init__()
        self.residual_beta = residual_beta

        self.inconv = nn.Sequential(
            nn.Conv2d(in_c,64,9,1,padding=4),
            nn.PReLU()
        )
        self.down1 = nn.Sequential(
            nn.Conv2d(64,64,3,stride = 1,padding = 1),
            nn.PReLU(),
            nn.Sequential(*[DenseBlock(64,beta = residual_beta) for _ in range(2)])
        )
        self.down2 = nn.Sequential(
            nn.Conv2d(64,128,3,stride = 1,padding = 1),
            nn.PReLU(),
            nn.Sequential(*[DenseBlock(128,beta = residual_beta) for _ in range(2)])

        )
        self.down3 = nn.Sequential(
            nn.Conv2d(128,256,3,stride = 1,padding = 1),
            nn.PReLU(),
            nn.Sequential(*[DenseBlock(256,beta = residual_beta) for _ in range(2)])
        )
        self.bottom = nn.Sequential(
            nn.Conv2d(256,512,3,1,padding = 1),
            nn.PReLU(),
            nn.Conv2d(512,512,3,stride = 1,padding=1),
            nn.PReLU(),
            nn.Conv2d(512,256,3,1,padding = 1),
            nn.PReLU()
        )
        self.up1 = nn.Sequential(
            nn.Conv2d(512,256,3,padding = 1),
            nn.PReLU(),
            nn.Sequential(*[DenseBlock(256,beta = residual_beta) for _ in range(2)]),
            nn.Conv2d(256,128,3,padding = 1),
            nn.PReLU()
        )
        self.up2 = nn.Sequential(
            nn.Conv2d(256,128,3,padding = 1),
            nn.PReLU(),
            nn.Sequential(*[DenseBlock(128,beta = residual_beta) for _ in range(2)]),
            nn.Conv2d(128,64,3,padding = 1),
            nn.PReLU()
        )
        self.up3 = nn.Sequential(
            nn.Conv2d(128,64,3,padding = 1),
            nn.PReLU(),
            nn.Sequential(*[DenseBlock(64,beta = residual_beta) for _ in range(2)]),
            nn.Conv2d(64,64,3,padding = 1),
            nn.PReLU()
        )
        self.out = nn.Conv2d(64,out_c,9,1,padding = 4)
    def forward(self,x):
        cin = self.inconv(x)
        down1 = self.down1(cin)
        downsample1 = F.avg_pool2d(down1,kernel_size = 2,stride = 2)
        down2 = self.down2(downsample1)
        downsample2 = F.avg_pool2d(down2,kernel_size = 2,stride = 2)
        down3 = self.down3(downsample2)
        downsample3 = F.avg_pool2d(down3,kernel_size = 2,stride = 2)

        bottom = self.bottom(downsample3)

        upsample1 = F.interpolate(bottom,scale_factor = 2)
        cat1 = torch.cat([down3,upsample1],dim = 1)
        up1 = self.up1(cat1)
        upsample2 = F.interpolate(up1,scale_factor = 2)
        cat2 = torch.cat([down2,upsample2],dim = 1)
        up2 = self.up2(cat2)
        upsample3 = F.interpolate(up2,scale_factor = 2)
        cat3 = torch.cat([down1,upsample3],dim = 1)
        up3 = self.up3(cat3)
        out = self.out(up3)
        out = (torch.tanh(out)+1)/2
        return out