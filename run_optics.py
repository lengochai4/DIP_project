"""Standalone Interactive Runner for STEM Optics Simulation Experiments.

Run directly via:
    python run_optics.py
    python run_optics.py --fullscreen
    python run_optics.py --lab lens
"""

import argparse
import sys
from pathlib import Path
import pygame

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from submission.stem_ui.optics.optics_experiments import OpticsLabSession
from submission.stem_ui.optics.optics_view import OpticsVisualizer


def main():
    parser = argparse.ArgumentParser(description="STEM Optics Interactive Simulator")
    parser.add_argument("--lab", choices=["refraction", "lens", "prism"], default="refraction",
                        help="Initial optics experiment to launch")
    parser.add_argument("--fullscreen", action="store_true", help="Launch in fullscreen mode")
    parser.add_argument("--width", type=int, default=1280, help="Initial window width")
    parser.add_argument("--height", type=int, default=800, help="Initial window height")
    args = parser.parse_args()

    pygame.init()
    pygame.font.init()

    flags = pygame.RESIZABLE
    if args.fullscreen:
        flags |= pygame.FULLSCREEN

    screen = pygame.display.set_mode((args.width, args.height), flags)
    pygame.display.set_caption("DIP STEM — Thí nghiệm Quang học (Optics)")
    clock = pygame.time.Clock()

    session = OpticsLabSession(initial_lab=args.lab)
    visualizer = OpticsVisualizer(session=session)

    print("=" * 60)
    print("DIP STEM — Phân hệ Mô phỏng Quang học (Optics)")
    print("Phím tắt điều khiển:")
    print("  • 1: Thí nghiệm Khúc xạ & Phản xạ toàn phần (Snell)")
    print("  • 2: Thấu kính mỏng (Hội tụ / Phân kì)")
    print("  • 3: Tán sắc ánh sáng qua Lăng kính")
    print("  • F / F11: Chuyển đổi Toàn màn hình")
    print("  • Q / ESC: Thoát chương trình")
    print("=" * 60)

    running = True
    fullscreen = args.fullscreen

    while running:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key == pygame.K_1:
                    session.select_lab("refraction")
                elif event.key == pygame.K_2:
                    session.select_lab("lens")
                elif event.key == pygame.K_3:
                    session.select_lab("prism")
                elif event.key in (pygame.K_f, pygame.K_F11):
                    fullscreen = not fullscreen
                    flags = pygame.RESIZABLE | (pygame.FULLSCREEN if fullscreen else 0)
                    screen = pygame.display.set_mode((screen.get_width(), screen.get_height()), flags)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                visualizer.handle_click(event.pos)
            elif event.type == pygame.VIDEORESIZE and not fullscreen:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

        visualizer.draw(screen, mouse_pos)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()

