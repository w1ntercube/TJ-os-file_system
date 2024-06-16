import os
from PyQt5.QtWidgets import (
    QMainWindow,
    QTreeWidget,
    QMenu,
    QInputDialog,
    QTextEdit,
    QMessageBox,
    QTreeWidgetItem,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QDialog,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from simple_file_system import FileSystem, FileControlBlock
from menu import create_menu_bar
import copy
from content_style import FileContentDialog

SAVE_FILENAME = "filesystem.dat"


class FileSystemGUI(QMainWindow):
    def __init__(self):
        super().__init__()

        # 默认开辟1MB的空间
        self.fs = FileSystem(1024 * 1024, 1024)

        if os.path.exists(SAVE_FILENAME):
            # 加载保存的文件系统
            self.fs.load_from_disk(SAVE_FILENAME)
        else:
            self.fs.format()  # 格式化文件系统

        self.initUI()

    def initUI(self):
        try:
            self.setWindowTitle("Simple File System")
            self.setWindowIcon(QIcon("images/simple_file_system.webp"))

            create_menu_bar(main_window=self)

            self.tree = QTreeWidget(self)
            self.tree.setHeaderLabel("File System")
            self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
            self.tree.customContextMenuRequested.connect(self.open_menu)

            # 添加双击链接
            # self.tree.itemDoubleClicked.connect(self.change_directory)
            self.tree.itemDoubleClicked.connect(self.select_item)

            self.tree.itemExpanded.connect(self.on_item_expanded)
            self.tree.itemCollapsed.connect(self.on_item_collapsed)

            # 创建根项目并填充树
            self.root_item = QTreeWidgetItem(self.tree)
            self.root_item.setText(0, "root")
            self.root_item.setData(0, Qt.UserRole, self.fs.root)
            self.root_item.setIcon(0, QIcon("images/directory.webp"))
            self.tree.addTopLevelItem(self.root_item)
            self.populate_tree(self.root_item, self.fs.root)

            # 创建只读文本器
            self.textEdit = QTextEdit(self)
            self.textEdit.setReadOnly(True)
            self.textEdit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

            splitter = QSplitter(Qt.Vertical)
            splitter.addWidget(self.tree)
            splitter.addWidget(self.textEdit)
            splitter.setStretchFactor(0, 1)
            splitter.setStretchFactor(1, 1)

            self.setCentralWidget(splitter)
            self.resize(1000, 800)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def populate_tree(self, parent_item, parent_fcb):
        # 填充子项目
        for name, fcb in parent_fcb.children.items():
            child_item = QTreeWidgetItem(parent_item)
            child_item.setText(0, name)
            child_item.setData(0, Qt.UserRole, fcb)
            if fcb.is_directory:
                child_item.setIcon(0, QIcon("images/directory.webp"))
                self.populate_tree(child_item, fcb)
            else:
                child_item.setIcon(0, QIcon("images/file.webp"))

    def get_full_path(self, fcb):
        path = []
        while fcb.name != "root":
            path.insert(0, fcb.name)
            parent_item = self.find_parent_item(fcb)
            fcb = parent_item.data(0, Qt.UserRole)
        return "/root/" + "/".join(path)

    def open_menu(self, position):
        item = self.tree.itemAt(position)
        if item:
            fcb = item.data(0, Qt.UserRole)
            menu = QMenu()

            if fcb.is_directory:
                # 目录有选项：创建文件、创建目录、删除、属性
                new_menu = menu.addMenu("New")
                new_file_act = new_menu.addAction("File")
                new_dir_act = new_menu.addAction("Directory")
                properties_act = menu.addAction("Properties")
                delete_act = menu.addAction("Delete")

                action = menu.exec_(self.tree.viewport().mapToGlobal(position))

                if action is None:
                    return

                if action == new_file_act:
                    self.create_entry(item, entry_type="File")
                elif action == new_dir_act:
                    self.create_entry(item, entry_type="Directory")
                elif action == delete_act:
                    self.delete_entry(item)
                elif action == properties_act:
                    self.show_properties(item)
            else:
                # 文件有选项：读、写、复制、属性、删除
                read_act = menu.addAction("Read")
                write_act = menu.addAction("Write")
                copy_act = menu.addAction("Copy")
                properties_act = menu.addAction("Properties")
                delete_act = menu.addAction("Delete")

                action = menu.exec_(self.tree.viewport().mapToGlobal(position))

                if action is None:
                    return

                if action == delete_act:
                    self.delete_entry(item)
                elif action == properties_act:
                    self.show_properties(item)
                elif action == read_act:
                    self.read_file(item)
                elif action == write_act:
                    self.write_file(item)
                elif action == copy_act:
                    self.copy_entry(item)

    def create_entry(self, parent_item, entry_type):
        name, ok = QInputDialog.getText(
            self, "Create Entry", f"Enter {entry_type.lower()} name:"
        )
        if ok and name:
            parent_fcb = parent_item.data(0, Qt.UserRole)

            if name in parent_fcb.children:
                # 如果与文件同名的目录或与目录同名的文件已经存在，自动添加后缀以区分
                existing_entry = parent_fcb.children[name]
                if existing_entry.is_directory and entry_type == "File":
                    name += "_file"
                elif not existing_entry.is_directory and entry_type == "Directory":
                    name += "_dir"

            if name in parent_fcb.children:
                # 如果与文件（或目录）同名的文件（或目录）已经存在，提示用户不能被创建
                existing_entry = parent_fcb.children[name]
                if existing_entry.is_directory and entry_type == "Directory":
                    QMessageBox.warning(
                        self,
                        "Warning",
                        f"A directory with the name {name} already exists in this directory!",
                    )
                    return
                elif not existing_entry.is_directory and entry_type == "File":
                    QMessageBox.warning(
                        self,
                        "Warning",
                        f"A file with the name {name} already exists in this directory!",
                    )
                    return

            if entry_type == "File":
                # 选择文件分配的空间大小
                size, ok = QInputDialog.getInt(
                    self,
                    "File Size",
                    "Enter file size (in KB):",
                    2,
                    1,
                    self.fs.size // 1024,
                )
                if ok:
                    size_in_bytes = size * 1024
                    self.fs.current_directory = parent_fcb
                    self.fs.create_file(name, size_in_bytes)
                    if name in self.fs.current_directory.children:
                        self.display_message(
                            f"File {name} created with size {size_in_bytes} bytes."
                        )
                        file_item = QTreeWidgetItem(parent_item)
                        file_item.setText(0, name)
                        file_item.setData(
                            0, Qt.UserRole, self.fs.current_directory.children[name]
                        )
                        file_item.setIcon(0, QIcon("images/file.webp"))

            elif entry_type == "Directory":
                self.fs.current_directory = parent_fcb
                self.fs.create_directory(name)
                self.display_message(f"Directory {name} created.")
                dir_item = QTreeWidgetItem(parent_item)
                dir_item.setText(0, name)
                dir_item.setData(
                    0, Qt.UserRole, self.fs.current_directory.children[name]
                )
                dir_item.setIcon(0, QIcon("images/directory.webp"))

            # 展开父项目以显示新创建的项目
            parent_item.setExpanded(True)

    def delete_entry(self, item):
        fcb = item.data(0, Qt.UserRole)
        if fcb == self.fs.root:
            # 不可以删除根目录
            QMessageBox.warning(
                self, "Warning", "You cannot delete the root directory!"
            )
            return

        parent_item = item.parent()
        # 如果父项目不存在，则默认为根目录
        parent_fcb = parent_item.data(0, Qt.UserRole) if parent_item else self.fs.root

        if fcb.is_directory:
            # 如果复制的项目在被删除的目录中，则清空复制的项目
            if self.fs.copied_entry and self.fs.is_fcb_in_directory(
                self.fs.copied_entry, fcb
            ):
                self.fs.copied_entry = None
                self.display_message(
                    "Copied content cleared because the directory is deleted."
                )
            self.fs.delete_directory(fcb.name)
            self.display_message(f"Directory {fcb.name} and its contents deleted.")
        else:
            if self.fs.copied_entry and self.fs.copied_entry.name == fcb.name:
                self.fs.copied_entry = None
                self.display_message(
                    "Copied content cleared because the file is deleted."
                )
            self.fs.delete_file(fcb.name)
            self.display_message(f"File {fcb.name} deleted.")

        if parent_item:
            index = parent_item.indexOfChild(item)
            parent_item.takeChild(index)
        else:
            self.tree.takeTopLevelItem(self.tree.indexOfTopLevelItem(item))

        if self.fs.current_directory == fcb:
            self.fs.current_directory = parent_fcb

    def delete_directory_recursively(self, fcb):
        for child_name in list(fcb.children.keys()):
            child_fcb = fcb.children[child_name]
            if child_fcb.is_directory:
                self.delete_directory_recursively(child_fcb)
            else:
                self.fs.delete_file(child_name)

        # 最后删除目录本身
        parent_fcb = self.fs.current_directory.children.get(fcb.name, None)
        if parent_fcb and parent_fcb.is_directory:
            del self.fs.current_directory.children[fcb.name]
            print(f"Directory {fcb.name} and its contents deleted.")

    def write_file(self, item):
        fcb = item.data(0, Qt.UserRole)
        full_path = self.get_full_path(fcb)
        # 保证目录被写入！
        if not fcb.is_directory:
            existing_data = self.fs.read_file(full_path)
            text, ok = QInputDialog.getMultiLineText(
                self, "Write File", "Enter file content:", existing_data or ""
            )
            if ok:
                self.fs.write_file(full_path, text.encode("utf-8"))
                self.display_message(f"Data written to file {full_path}.")

    def read_file(self, item):
        fcb = item.data(0, Qt.UserRole)
        full_path = self.get_full_path(fcb)
        # 保证不是目录被读取！
        if not fcb.is_directory:
            data = self.fs.read_file(full_path)
            if data:
                dialog = FileContentDialog(
                    f"Content of {fcb.name}", f"File: {fcb.name}\n\n{data}", self
                )
                dialog.exec_()
            else:
                self.display_message(f"File {fcb.name} is empty.")

    def find_parent_item(self, fcb):
        def recursive_find(item, target_fcb):
            for i in range(item.childCount()):
                child = item.child(i)
                if child.data(0, Qt.UserRole) == target_fcb:
                    return item
                result = recursive_find(child, target_fcb)
                if result:
                    return result
            return None

        return recursive_find(self.root_item, fcb)

    def copy_entry(self, item):
        if item is None:
            item = self.tree.currentItem()
        if item is None:
            self.display_message("No file or directory selected to copy.")
            return

        fcb = item.data(0, Qt.UserRole)
        if fcb is None:
            self.display_message("Invalid item selected.")
            return

        if fcb is self.fs.root:
            self.display_message("Cannot copy the root directory.")
            return

        self.fs.copy_entry(fcb.name)
        self.display_message(f"Copied {fcb.name}.")

    def paste_entry(self, item=None):
        if not self.fs.copied_entry:
            self.display_message("Nothing to paste. Please copy a file first.")
            return

        if self.fs.copied_entry.is_directory:
            # 只支持文件复制
            self.display_message("Cannot paste a directory. Only files can be pasted.")
            return

        target_fcb = self.fs.current_directory
        if item:
            target_fcb = item.data(0, Qt.UserRole)

        if target_fcb is None or not target_fcb.is_directory:
            self.display_message("Invalid target. Please select a directory for paste.")
            return

        copied_name = self.fs.copied_entry.name
        new_name = copied_name
        count = 1
        # 确保新名称不与目标目录中的文件或目录同名
        while new_name in target_fcb.children:
            new_name = f"{copied_name} ({count})"
            count += 1

        new_entry = copy.deepcopy(self.fs.copied_entry)
        new_entry.name = new_name
        target_fcb.children[new_name] = new_entry

        # 清空剪贴板，确保文件只能被粘贴一次，并防止恢复删除的内容
        self.fs.copied_entry = None

        self.display_message(f"Pasted {new_entry.name} into {target_fcb.name}.")
        self.refresh_view()

    def _update_fcb_references(self, fcb, parent):
        # 更新 fcb 引用
        for name, child in fcb.children.items():
            if child.is_directory:
                self._update_fcb_references(child, fcb)
            parent.children[name] = child

    def change_directory(self, item, column):
        fcb = item.data(0, Qt.UserRole)
        if fcb.is_directory:
            self.fs.current_directory = fcb
            self.display_message(f"Changed directory to {fcb.name}.")
        else:
            self.read_file(item)

    def select_item(self, item, column):
        # 捕获双击事件以选择项目
        fcb = item.data(0, Qt.UserRole)
        self.tree.setCurrentItem(item)
        if not fcb.is_directory:
            self.read_file(item)

    def on_item_expanded(self, item):
        # 捕获项目展开事件
        fcb = item.data(0, Qt.UserRole)
        if fcb.is_directory:
            self.display_message(f"Directory {fcb.name} expanded.")

    def on_item_collapsed(self, item):
        # 捕获项目折叠事件
        fcb = item.data(0, Qt.UserRole)
        if fcb.is_directory:
            self.display_message(f"Directory {fcb.name} collapsed.")

    def closeEvent(self, event):
        reply = QMessageBox.information(
            self,
            "Message",
            "Do you want to quit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.fs.save_to_disk(SAVE_FILENAME)
            info = QMessageBox.information(
                self,
                "Simple File System Saved",
                f"File system has been updated to {SAVE_FILENAME}.",
                QMessageBox.Ok,
            )
            if info:
                event.accept()
        else:
            event.ignore()

    def display_message(self, message):
        self.textEdit.append(message)

    def show_properties(self, item):
        fcb = item.data(0, Qt.UserRole)

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Properties of {fcb.name}")

        table = QTableWidget(dialog)
        table.setRowCount(3 if fcb.is_directory else 2)
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Property", "Value"])
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        table.setItem(0, 0, QTableWidgetItem("Name"))
        table.setItem(0, 1, QTableWidgetItem(fcb.name))

        if fcb.is_directory:
            num_files = len(
                [child for child in fcb.children.values() if not child.is_directory]
            )
            num_dirs = len(
                [child for child in fcb.children.values() if child.is_directory]
            )
            table.setItem(1, 0, QTableWidgetItem("Type"))
            table.setItem(1, 1, QTableWidgetItem("Directory"))
            table.setItem(2, 0, QTableWidgetItem("Contents"))
            table.setItem(
                2,
                1,
                QTableWidgetItem(f"Subdirectories: {num_dirs}, Files: {num_files}"),
            )
        else:
            table.setItem(1, 0, QTableWidgetItem("Type"))
            table.setItem(1, 1, QTableWidgetItem("File"))
            table.setItem(2, 0, QTableWidgetItem("Size"))
            table.setItem(2, 1, QTableWidgetItem(f"{fcb.size} bytes"))

        layout = QVBoxLayout(dialog)
        layout.addWidget(table)
        dialog.setLayout(layout)
        dialog.resize(700, 400)
        dialog.exec_()

    def show_properties_from_menu(self):
        item = self.tree.currentItem()
        if item:
            self.show_properties(item)
        else:
            QMessageBox.warning(self, "Warning", "No file or directory selected.")

    def save_and_notify(self):
        self.fs.save_to_disk(SAVE_FILENAME)
        self.display_message(f"File system saved to {SAVE_FILENAME}.")

    def create_file_in_current_directory(self):
        self.create_entry_in_current_directory("File")

    def create_directory_in_current_directory(self):
        self.create_entry_in_current_directory("Directory")

    def create_entry_in_current_directory(self, entry_type):
        if (
            not self.fs.current_directory
            or self.fs.current_directory.name not in self.fs.root.children
        ):  # 排除当前目录不存在的情况
            self.display_message("Current directory is invalid. Resetting to root.")
            self.fs.current_directory = self.fs.root
            parent_item = self.root_item
        else:
            parent_item = self.find_item_by_fcb(self.fs.current_directory)

        self.create_entry(parent_item, entry_type)

    def validate_current_directory(self):
        if (
            not self.fs.current_directory
            or self.fs.current_directory.name not in self.fs.root.children
        ):
            self.display_message("Current directory is invalid. Resetting to root.")
            self.fs.current_directory = self.fs.root
            return self.root_item
        return self.find_item_by_fcb(self.fs.current_directory)

    def find_item_by_fcb(self, fcb):
        # 递归查找项目
        def recursive_find(item, target_fcb):
            if item.data(0, Qt.UserRole) == target_fcb:
                return item
            for i in range(item.childCount()):
                child = item.child(i)
                result = recursive_find(child, target_fcb)
                if result:
                    return result
            return None

        return recursive_find(self.root_item, fcb)

    def rename_entry(self):
        item = self.tree.currentItem()
        if item:
            name, ok = QInputDialog.getText(self, "Rename", "Enter new name:")
            if ok and name:
                fcb = item.data(0, Qt.UserRole)
                fcb.name = name
                item.setText(0, name)
                self.display_message(f"Renamed to {name}.")

    def refresh_view(self):
        expanded_items = self.get_expanded_items(self.root_item)
        self.tree.clear()

        self.root_item = QTreeWidgetItem(self.tree)
        self.root_item.setText(0, "root")
        self.root_item.setData(0, Qt.UserRole, self.fs.root)
        self.root_item.setIcon(0, QIcon("images/directory.webp"))
        self.tree.addTopLevelItem(self.root_item)
        self.populate_tree(self.root_item, self.fs.root)

        self.expand_items(expanded_items)
        self.display_message("View refreshed.")

    def get_expanded_items(self, item):
        expanded_items = []
        if item.isExpanded():
            expanded_items.append(item.data(0, Qt.UserRole).name)
        for i in range(item.childCount()):
            child_item = item.child(i)
            # 递归获取展开的项目
            expanded_items.extend(self.get_expanded_items(child_item))
        return expanded_items

    def expand_items(self, expanded_items):
        for name in expanded_items:
            item = self.find_item_by_name(self.root_item, name)
            if item:
                item.setExpanded(True)

    def find_item_by_name(self, parent_item, name):
        if parent_item.data(0, Qt.UserRole).name == name:
            return parent_item
        for i in range(parent_item.childCount()):
            child_item = parent_item.child(i)
            found_item = self.find_item_by_name(child_item, name)
            if found_item:
                return found_item
        return None

    def show_about(self):
        about_message = (
            "This is a Simple File System with GUI\n"
            "Version 1.0\n\n"
            "How to use this file system:\n"
            "1. To create a new file or directory, right-click on a directory and select 'New'.\n"
            "2. To delete a file or directory, right-click on it and select 'Delete'.\n"
            "3. To read a file, right-click on it and select 'Read'. The content will be displayed in a scrollable dialog.\n"
            "4. To write to a file, right-click on it and select 'Write'. You can enter the content in the dialog.\n"
            "5. To copy a file, right-click on it and select 'Copy'. Then navigate to the target directory, right-click, and select 'Paste'.\n"
            "6. To view properties of a file or directory, right-click on it and select 'Properties'.\n"
            "7. Use the 'Refresh' option in the 'View' menu to refresh the file system view.\n"
            "8. Use the 'Format' option in the 'Tools' menu to format the file system (this is an irreversible operation, and all data will be lost).\n"
            "9. Use the 'Save' option in the 'File' menu to save the current state of the file system.\n"
            "10. Use the 'Open' option in the 'File' menu to open and load a previously saved file system state.\n"
        )
        about_dialog = QMessageBox(self)
        about_dialog.setWindowTitle("About")
        about_dialog.setText(about_message)
        about_dialog.setStandardButtons(QMessageBox.Ok)
        about_dialog.exec_()

    def format_disk(main_window):
        reply = QMessageBox.question(
            main_window,
            "Confirm Format",
            "Are you sure you want to format the file system? This will delete all data.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            main_window.fs.format()  # 调用文件系统的格式化方法
            main_window.refresh_view()  # 刷新视图
            main_window.display_message("File system formatted.")
