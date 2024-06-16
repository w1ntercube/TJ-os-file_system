from PyQt5.QtWidgets import QAction


def create_menu_bar(main_window):
    menubar = main_window.menuBar()

    # File Menu
    file_menu = menubar.addMenu("File")

    new_file_action = QAction("New File", main_window)
    new_file_action.triggered.connect(
        lambda: main_window.create_file_in_current_directory()
    )
    file_menu.addAction(new_file_action)

    new_dir_action = QAction("New Directory", main_window)
    new_dir_action.triggered.connect(
        lambda: main_window.create_directory_in_current_directory()
    )
    file_menu.addAction(new_dir_action)

    open_action = QAction("Open", main_window)
    open_action.triggered.connect(lambda: main_window.open_entry())
    file_menu.addAction(open_action)

    save_action = QAction("Save", main_window)
    save_action.triggered.connect(lambda: main_window.save_and_notify())
    file_menu.addAction(save_action)

    copy_action = QAction("Copy", main_window)
    copy_action.triggered.connect(lambda: main_window.copy_entry(None))
    file_menu.addAction(copy_action)

    paste_action = QAction("Paste", main_window)
    paste_action.triggered.connect(lambda: main_window.paste_entry())
    file_menu.addAction(paste_action)

    exit_action = QAction("Exit", main_window)
    exit_action.triggered.connect(main_window.close)
    file_menu.addAction(exit_action)

    # Edit Menu
    edit_menu = menubar.addMenu("Edit")

    rename_action = QAction("Rename", main_window)
    rename_action.triggered.connect(lambda: main_window.rename_entry())
    edit_menu.addAction(rename_action)

    delete_action = QAction("Delete", main_window)
    delete_action.triggered.connect(
        lambda: main_window.delete_entry(main_window.tree.currentItem())
    )
    edit_menu.addAction(delete_action)

    # View Menu
    view_menu = menubar.addMenu("View")

    refresh_action = QAction("Refresh", main_window)
    refresh_action.triggered.connect(lambda: main_window.refresh_view())
    view_menu.addAction(refresh_action)

    properties_action_view = QAction("Properties", main_window)
    properties_action_view.triggered.connect(
        lambda: main_window.show_properties(main_window.tree.currentItem())
    )
    view_menu.addAction(properties_action_view)

    # Tools Menu
    tools_menu = menubar.addMenu("Tools")

    format_action = QAction("Format", main_window)
    format_action.triggered.connect(lambda: main_window.format_disk())
    tools_menu.addAction(format_action)

    # Help Menu
    help_menu = menubar.addMenu("Help")

    about_action = QAction("About", main_window)
    about_action.triggered.connect(lambda: main_window.show_about())
    help_menu.addAction(about_action)
