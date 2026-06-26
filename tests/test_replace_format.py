"""
replace_texture가 의존하는 핵심 보장 검증:
  set_image(target_format=원본) → 원본 포맷이 유지되고, 색이 밝아지지 않음(감마 시프트 없음).
이 두 가지가 깨지면 "밝아짐/보라색/포맷 손실" 버그가 재발한다.

실행: python tests/test_replace_format.py   (프레임워크 없이 assert만 사용)
"""
import numpy as np
from PIL import Image
from UnityPy.export import Texture2DConverter as T
from UnityPy.enums import TextureFormat as TF
from texture2ddecoder import decode_bc7, decode_bc3, decode_bc1
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from core.texture_processor import TextureProcessor

# 알려진 색 패턴(그라데이션). 단색은 압축 오차를 못 잡으므로 변화를 줌.
img = Image.new("RGBA", (64, 64))
img.putdata([((x * 4) % 256, (y * 4) % 256, 128, 255) for y in range(64) for x in range(64)])
orig = np.array(img).astype(int)[:, :, :3]

CASES = [
    (TF.BC7, decode_bc7, 8),    # 거의 무손실
    (TF.DXT5, decode_bc3, 16),  # BC3, 블록 압축 오차 허용
    (TF.DXT1, decode_bc1, 24),  # 4:1, 오차 큼
]

for fmt, decode, max_mean_err in CASES:
    enc, tf = T.image_to_texture2d(img, fmt, flip=False)
    # 1) 요청한 포맷이 그대로 유지돼야 함 (RGBA32로 떨어지면 안 됨)
    assert tf == fmt, f"{fmt.name}: 포맷이 {tf.name}로 바뀜 (원본 포맷 유지 실패)"

    dec = np.frombuffer(bytes(decode(enc, 64, 64)), dtype=np.uint8).reshape(64, 64, 4).astype(int)
    dec_rgb = dec[:, :, [2, 1, 0]]  # 디코더는 BGRA 반환 → RGB로 스왑
    mean_err = np.abs(dec_rgb - orig).mean()
    # 2) 색 오차가 작아야 함 (압축 오차 수준)
    assert mean_err < max_mean_err, f"{fmt.name}: 색 오차 과다 {mean_err:.1f}"
    # 3) 밝아짐(감마 시프트) 없어야 함: 평균 밝기 편차가 한 자릿수
    brightness_shift = dec_rgb.mean() - orig.mean()
    assert abs(brightness_shift) < 6, f"{fmt.name}: 밝기 시프트 {brightness_shift:+.1f} (밝아짐 버그 재발)"
    print(f"OK {fmt.name}: 포맷유지 색오차={mean_err:.2f} 밝기시프트={brightness_shift:+.2f}")

print("PASS: 원본 포맷 유지 + 색/밝기 보존 확인")


class FakeTextureData:
    def __init__(self):
        self.m_Name = "fake"
        self.m_TextureFormat = TF.BC7
        self.m_Width = 16
        self.m_Height = 16
        self.m_MipCount = 4
        self.calls = []
        self.saved = False

    def set_image(self, image, target_format=None, mipmap_count=1):
        self.calls.append((image.size, image.mode, target_format, mipmap_count))

    def save(self):
        self.saved = True


with tempfile.TemporaryDirectory() as temp_dir:
    input_path = Path(temp_dir) / "input.png"
    Image.new("P", (8, 8)).save(input_path)

    fake_data = FakeTextureData()
    assert TextureProcessor().replace_texture(None, fake_data, str(input_path))
    assert fake_data.saved
    assert fake_data.calls == [((16, 16), "RGBA", TF.BC7, 4)]

print("PASS: replace_texture가 원본 포맷/밉맵으로 set_image 호출 확인")
