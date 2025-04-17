from moviepy.editor import *
import numpy as np

# 画像32枚を読み込み
image_files = [f"image_{i:02}.jpeg" for i in range(32)]
images = [ImageClip(img).resize(height=100) for img in image_files]  # 1タイルの高さ100px

# 4x4 = 16枚ずつ、タイル状に配置
tile_width = images[0].w
tile_height = images[0].h
frame_w = tile_width * 4
frame_h = tile_height * 4

# 全画像を横に8列（4x8 = 32枚）並べる
tile_grid = []
for row in range(4):
    row_imgs = images[row*8:(row+1)*8]
    row_strip = clips_array([[clip] for clip in row_imgs])
    tile_grid.append(row_strip)

strip = clips_array([tile_grid])

# スライド用のアニメーション（左→右）
def move_frame(t):
    x = - (tile_width * 4) * (t / 4)  # 4秒で1画面分（4列）スライド
    return strip.set_position((x, 0))

animated = strip.set_duration(4).set_position(lambda t: (-tile_width * 4 * t / 4, 0))

# 動画として書き出し
final = CompositeVideoClip([animated], size=(frame_w, frame_h))
final.write_videofile("sliding_tiles.mp4", fps=30)

