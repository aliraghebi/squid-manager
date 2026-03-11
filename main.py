#!/usr/bin/env python3
import sys
import curses
from lib.tui import setup_colors, user_list_screen, draw_help
from lib.user_mgmt import add_user, change_password, delete_user

MENU_ITEMS = ["User List", "Create User", "Change Password", "Delete User", "Quit"]

def main_menu(stdscr):
    curses.curs_set(0)
    setup_colors()
    selected_idx = 0

    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "SQUID MANAGER\n", curses.A_BOLD | curses.color_pair(4))
        for idx, item in enumerate(MENU_ITEMS):
            color = curses.A_REVERSE if idx == selected_idx else curses.A_NORMAL
            stdscr.addstr(2 + idx, 0, item, color)
        draw_help(stdscr, "↑↓ Navigate  ENTER Select  Q Quit")
        stdscr.refresh()

        key = stdscr.getch()
        if key in (curses.KEY_UP, ord('k')):
            selected_idx = max(0, selected_idx - 1)
        elif key in (curses.KEY_DOWN, ord('j')):
            selected_idx = min(len(MENU_ITEMS) - 1, selected_idx + 1)
        elif key in (10, 13):
            choice = MENU_ITEMS[selected_idx]
            if choice == "User List":
                user_list_screen(stdscr)
            elif choice == "Create User":
                add_user(stdscr)
            elif choice == "Change Password":
                change_password(stdscr)
            elif choice == "Delete User":
                delete_user(stdscr)
            elif choice == "Quit":
                sys.exit(0)
        elif key in (ord('q'), ord('Q')):
            sys.exit(0)


if __name__ == "__main__":
    try:
        curses.wrapper(main_menu)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)