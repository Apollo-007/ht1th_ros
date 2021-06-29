#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from collections import OrderedDict
import torch
import torch.nn as nn
import numpy as np


class UNet(nn.Module):
	def __init__(self, in_channels=3, out_channels=1, init_features=32, WithActivateLast = True, ActivateFunLast = None):
		super(UNet, self).__init__()   # define net structure
		features = init_features
		self.WithActivateLast = WithActivateLast      # activate last layer
		self.ActivateFunLast = ActivateFunLast
		self.encoder1 = UNet._block(in_channels, features, name="enc1")
		self.pool1 = nn.MaxPool2d(kernel_size=2, stride=2)
		self.encoder2 = UNet._block(features, features * 2, name="enc2")
		self.pool2 = nn.MaxPool2d(kernel_size=2, stride=2)
		self.encoder3 = UNet._block(features * 2, features * 4, name="enc3")
		self.pool3 = nn.MaxPool2d(kernel_size=2, stride=2)
		self.encoder4 = UNet._block(features * 4, features * 8, name="enc4")
		self.pool4 = nn.MaxPool2d(kernel_size=2, stride=2)
		self.encoder5 = UNet._block(features * 8, features * 16, name="enc5")
		self.pool5 = nn.MaxPool2d(kernel_size=2, stride=2)

		self.bottleneck = UNet._block(features * 16, features * 32, name="bottleneck")

		self.upconv5 = nn.ConvTranspose2d(
			features * 32, features * 16, kernel_size=2, stride=2
		)
		self.decoder5 = UNet._block((features * 16) * 2, features * 16, name="dec5")

		self.upconv4 = nn.ConvTranspose2d(
			features * 16, features * 8, kernel_size=2, stride=2
		)
		self.decoder4 = UNet._block(features * 16, features * 8, name="dec4")
		self.upconv3 = nn.ConvTranspose2d(
			features * 8, features * 4, kernel_size=2, stride=2
		)
		self.decoder3 = UNet._block((features * 4) * 2, features * 4, name="dec3")
		self.upconv2 = nn.ConvTranspose2d(
			features * 4, features * 2, kernel_size=2, stride=2
		)
		self.decoder2 = UNet._block((features * 2) * 2, features * 2, name="dec2")
		self.upconv1 = nn.ConvTranspose2d(
			features * 2, features, kernel_size=2, stride=2
		)
		self.decoder1 = UNet._block(features * 2, features, name="dec1")
		self.conv = nn.Conv2d(
			in_channels=features, out_channels=out_channels, kernel_size=1
		)

	def forward(self, x):

		enc1 = self.encoder1(x)
		enc2 = self.encoder2(self.pool1(enc1))
		enc3 = self.encoder3(self.pool2(enc2))
		enc4 = self.encoder4(self.pool3(enc3))
		enc5 = self.encoder5(self.pool4(enc4))

		bottleneck = self.bottleneck(self.pool5(enc5))


		dec5 = self.upconv5(bottleneck)
		dec5 = torch.cat((dec5, enc5), dim=1)
		dec5 = self.decoder5(dec5)

		dec4 = self.upconv4(dec5)
		dec4 = torch.cat((dec4, enc4), dim=1)
		dec4 = self.decoder4(dec4)

		dec3 = self.upconv3(dec4)
		dec3 = torch.cat((dec3, enc3), dim=1)
		dec3 = self.decoder3(dec3)

		dec2 = self.upconv2(dec3)
		dec2 = torch.cat((dec2, enc2), dim=1)
		dec2 = self.decoder2(dec2)

		dec1 = self.upconv1(dec2)
		dec1 = torch.cat((dec1, enc1), dim=1)
		dec1 = self.decoder1(dec1)  # 2*32*256*256
		if self.WithActivateLast:
			# return torch.sigmoid(self.conv(dec1))  # BS*1*256*256
			return self.ActivateFunLast(self.conv(dec1))
		else:
			return self.conv(dec1)  # BS*1*256*256


	@staticmethod
	def _block(in_channels, features, name):
		return nn.Sequential(
			OrderedDict(
				[
					(
						name + "conv1",
						nn.Conv2d(
							in_channels=in_channels,
							out_channels=features,
							kernel_size=3,
							padding=1,
							bias=False,
						),
					),
					(name + "norm1", nn.BatchNorm2d(num_features=features)),
					(name + "relu1", nn.ReLU(inplace=True)),
					(
						name + "conv2",
						nn.Conv2d(
							in_channels=features,
							out_channels=features,
							kernel_size=3,
							padding=1,
							bias=False,
						),
					),
					(name + "norm2", nn.BatchNorm2d(num_features=features)),
					(name + "relu2", nn.ReLU(inplace=True)),
				]
			)
		)


if __name__ == '__main__':
	Input = torch.randn((2, 1, 256, 256))
	Target = torch.empty((2, 1, 256, 256), dtype=torch.long).random_(2)

	Unet = UNet(in_channels=1, out_channels=2)
	LossFun = nn.CrossEntropyLoss()
	Output = Unet(Input)
	print(Output.shape)
	print(Target.shape)


	BatchLoss = LossFun(Output, Target[:, 0, :, :])
	print(BatchLoss)


	Errs = []
	for i, Sample in enumerate(Output):
		for j in range(256):
			for k in range(256):
				temppredict = Output[i, :, j, k]
				temptarget = Target[i, 0, j, k]
				err = -temppredict[temptarget] + torch.log(torch.sum(np.e ** temppredict))
				Errs.append(err.detach().numpy())
	print(np.mean(Errs))

