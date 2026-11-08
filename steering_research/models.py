"""Wheel-angle estimators: image-only CNN and temporal CNN+GRU(+flow).
No model is called calibrated until evaluated on held-out, labelled videos.
"""
from __future__ import annotations
import torch
from torch import nn
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights


def build_encoder(pretrained: bool = False, freeze: bool = True) -> nn.Module:
    weights = EfficientNet_B0_Weights.DEFAULT if pretrained else None
    model = efficientnet_b0(weights=weights)
    model.classifier = nn.Identity()  # EfficientNet-B0 pooled features: 1280 dimensions
    if freeze:
        for param in model.parameters(): param.requires_grad_(False)
        model.eval()
    return model


class SteeringRegressor(nn.Module):
    """Input: frames [B,T,3,224,224], flow [B,T,3] when requested.

    Output: predicted signed wheel rotation in degrees at FINAL frame in sequence.
    ``cnn`` predicts from final frame only; temporal modes use causal GRU.
    """
    def __init__(self, mode: str = 'cnn_gru_flow', pretrained: bool = False, freeze_encoder: bool = True, hidden: int = 96):
        super().__init__()
        if mode not in ('cnn','cnn_gru','cnn_gru_flow'):
            raise ValueError(f'Unknown model mode: {mode}')
        self.mode = mode
        self.freeze_encoder = freeze_encoder
        self.encoder = build_encoder(pretrained=pretrained, freeze=freeze_encoder)
        if mode == 'cnn':
            self.head = nn.Sequential(nn.Linear(1280,128), nn.ReLU(), nn.Dropout(.1), nn.Linear(128,1))
        else:
            self.gru = nn.GRU(1280 + (3 if mode.endswith('_flow') else 0), hidden, batch_first=True)
            self.head = nn.Sequential(nn.Linear(hidden,64),nn.ReLU(),nn.Linear(64,1))

    def train(self, mode: bool = True):
        super().train(mode)
        if self.freeze_encoder: self.encoder.eval()
        return self

    def forward(self, frames: torch.Tensor, flow: torch.Tensor | None = None):
        b,t,c,h,w = frames.shape
        frames_in = frames[:,-1:] if self.mode=='cnn' else frames
        with torch.no_grad() if self.freeze_encoder else torch.enable_grad():
            features = self.encoder(frames_in.reshape(-1,c,h,w)).reshape(b,frames_in.shape[1],-1)
        if self.mode=='cnn':
            return self.head(features[:,-1,:]).squeeze(-1)
        if self.mode=='cnn_gru_flow':
            if flow is None or flow.shape != (b,t,3):
                raise ValueError('cnn_gru_flow requires flow tensor [batch, time, 3]')
            features = torch.cat([features,flow],dim=-1)
        sequence,_ = self.gru(features)
        return self.head(sequence[:,-1,:]).squeeze(-1)
