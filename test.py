import torch
print('=== RTX 4090 Test ===')
print(f'PyTorch: {torch.__version__}')
print(f'CUDA: {torch.cuda.is_available()}')
print(f'GPU: {torch.cuda.get_device_name()}')
print(f'GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB')

  # Test operations
x = torch.randn(1000, 1000, device='cuda')
y = torch.mm(x, x.t())
print('✅ Basic operations work')

# Test mixed precision (ważne dla RTX 4090)
x = x.half()
y = torch.mm(x, x.t())
print('✅ FP16 operations work')

print('🚀 RTX 4090 ready for training!')