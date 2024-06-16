import os
import pickle
import copy
from PyQt5.QtWidgets import QMessageBox


class FileControlBlock:
    def __init__(self, name, is_directory, size=0, address=-1):
        self.name = name
        self.is_directory = is_directory
        self.size = size
        self.address = address
        self.children = {}  # 字典，只有当 is_directory 为 True 时才有意义


class FileSystem:
    def __init__(self, size, block_size):
        self.size = size
        self.block_size = block_size
        self.num_blocks = size // block_size
        self.storage = bytearray(size)  # 存储器，存放文件数据
        self.bitmap = [0] * self.num_blocks  # 位图，记录哪些块被占用
        self.fat = [-1] * self.num_blocks  # FAT，记录每个块的下一个块号
        self.root = FileControlBlock("root", True)
        self.current_directory = self.root
        self.copied_entry = None  # 是否有复制文件

    def format(self):
        self.storage = bytearray(self.size)
        self.bitmap = [0] * self.num_blocks  # 0表示空闲，1表示已占用
        self.fat = [-1] * self.num_blocks  # -1表示未分配
        self.root = FileControlBlock("root", True)
        self.current_directory = self.root
        self.copied_entry = None
        print("File system formatted.")

    def save_to_disk(self, filename):
        with open(filename, "wb") as f:
            pickle.dump((self.storage, self.bitmap, self.fat, self.root), f)
        print(f"File system saved to {filename}.")

    def load_from_disk(self, filename):
        if os.path.exists(filename):
            try:  # 尝试加载文件系统
                with open(filename, "rb") as f:
                    self.storage, self.bitmap, self.fat, self.root = pickle.load(f)
                    self.current_directory = self.root
                print(f"File system loaded from {filename}.")
            except (pickle.UnpicklingError, EOFError, AttributeError) as e:
                print(f"Failed to load file system from {filename}: {str(e)}")
                self.format()  # 重新格式化文件系统
        else:
            print(f"{filename} does not exist.")

    def allocate_block(self):
        for i in range(self.num_blocks):
            if self.bitmap[i] == 0:
                self.bitmap[i] = 1
                return i
        error_message = "No free blocks available."
        print(error_message)
        QMessageBox.warning(
            None,
            "Error",
            error_message,
        )
        return -1

    def free_block(self, block_num):
        self.bitmap[block_num] = 0
        self.fat[block_num] = -1

    def create_file(self, name, size):
        if name in self.current_directory.children:
            print(f"File or directory {name} already exists.")
            return
        num_blocks_needed = (size + self.block_size - 1) // self.block_size  # 向上取整

        # 检查是否有足够的空闲块
        if self.bitmap.count(0) < num_blocks_needed:
            error_message = f"Not enough space to create file {name}."
            print(error_message)
            QMessageBox.warning(
                None,
                "Error",
                error_message,
            )
            return

        blocks = []
        try:
            for _ in range(num_blocks_needed):
                blocks.append(self.allocate_block())
        except Exception as e:
            for block in blocks:
                self.free_block(block)
            print(f"Failed to create file {name}: {str(e)}")
            return
        for i in range(num_blocks_needed - 1):
            self.fat[blocks[i]] = blocks[i + 1]  # 链接各个块
        self.fat[blocks[-1]] = -1  # 最后一个块指向 -1 表示结束
        fcb = FileControlBlock(name, False, size, blocks[0])  # 创建文件控制块
        self.current_directory.children[name] = fcb  # 加入当前目录
        print(f"File {name} created.")

    def clear_file_data(self, fcb):
        block = fcb.address
        while block != -1:
            next_block = self.fat[block]  # 得到下一个块号
            # 清空数据块
            self.storage[block * self.block_size : (block + 1) * self.block_size] = (
                bytearray(self.block_size)
            )  # 将当前块的所有字节重置为 0（通过创建一个新的空字节数组 bytearray(self.block_size)）。
            self.free_block(block)
            block = next_block

    def delete_file(self, name):
        if name in self.current_directory.children:
            fcb = self.current_directory.children[name]
            if not fcb.is_directory:
                # 如果复制的文件被删除，则清空剪贴板内容
                if self.copied_entry and self.copied_entry.name == fcb.name:
                    self.copied_entry = None
                    error_message = (
                        "Copied content cleared because the file is deleted."
                    )
                    print(error_message)
                    QMessageBox.information(
                        None,
                        "Clipboard Cleared",
                        error_message,
                    )

                block = fcb.address
                while block != -1:
                    next_block = self.fat[block]
                    self.storage[
                        block * self.block_size : (block + 1) * self.block_size
                    ] = bytearray(self.block_size)
                    self.free_block(block)
                    block = next_block

                del self.current_directory.children[name]
                print(f"File {name} deleted.")
            else:
                print(f"{name} is not a file.")
        else:
            print(f"File {name} not found.")

    def create_directory(self, name):
        if name in self.current_directory.children:
            print(f"File or directory {name} already exists.")
            return
        fcb = FileControlBlock(name, True)
        self.current_directory.children[name] = fcb
        print(f"Directory {name} created.")

    def delete_directory(self, name):
        if name in self.current_directory.children:
            fcb = self.current_directory.children[name]
            if fcb.is_directory:
                # 检查剪贴板内容是否在将要删除的目录中
                if self.copied_entry and self.is_fcb_in_directory(
                    self.copied_entry, fcb
                ):
                    self.copied_entry = None
                    error_message = (
                        "Copied content cleared because the directory is deleted."
                    )
                    print(error_message)
                    QMessageBox.information(
                        None,
                        "Clipboard Cleared",
                        error_message,
                    )

                # 递归删除子目录和文件
                for sub_entry in list(fcb.children.keys()):
                    if fcb.children[sub_entry].is_directory:
                        self.delete_directory(sub_entry)
                    else:
                        self.delete_file(sub_entry)

                del self.current_directory.children[name]
                print(f"Directory {name} and its contents deleted.")
            else:
                print(f"{name} is not a directory.")
        else:
            print(f"Directory {name} not found.")

    def is_fcb_in_directory(self, fcb, directory):
        # 判断文件控制块是否在目录中
        if fcb in directory.children.values():
            return True
        for child in directory.children.values():
            if child.is_directory and self.is_fcb_in_directory(fcb, child):
                return True
        return False

    def change_directory(self, path):
        if path == "..":
            # 回到上一级目录
            if self.current_directory.name != "root":
                self.current_directory = self.root
            else:
                print("Already at the root directory.")
        elif path in self.current_directory.children:
            # 进入子目录
            fcb = self.current_directory.children[path]
            if fcb.is_directory:
                self.current_directory = fcb
                print(f"Changed directory to {path}.")
            else:
                print(f"{path} is not a directory.")
        else:
            print(f"Directory {path} not found.")

    def open_file(self, path):
        fcb = self.find_fcb_by_path(path)
        if fcb and not fcb.is_directory:
            fcb.is_open = True
            print(f"File {path} opened.")
        else:
            print(f"File {path} not found or is a directory.")

    def close_file(self, path):
        fcb = self.find_fcb_by_path(path)
        if fcb and not fcb.is_directory and hasattr(fcb, "is_open") and fcb.is_open:
            fcb.is_open = False
            print(f"File {path} closed.")
        else:
            print(f"File {path} is not open or is a directory.")

    def write_file(self, path, data):
        fcb = self.find_fcb_by_path(path)
        if fcb is None:
            print(f"File {path} not found.")
            return

        if fcb.is_directory:
            print(f"{path} is a directory, cannot write to it.")
            return

        if not hasattr(fcb, "is_open") or not fcb.is_open:
            self.open_file(path)

        current_size = len(data)
        num_blocks_needed = (current_size + self.block_size - 1) // self.block_size

        # 检查是否有足够的空闲块
        if self.bitmap.count(0) < num_blocks_needed:
            error_message = f"Not enough space to write to file {path}."
            print(error_message)
            QMessageBox.warning(
                None,
                "Error",
                error_message,
            )
            return

        # 清空原有文件数据
        self.clear_file_data(fcb)

        blocks = []
        try:
            for _ in range(num_blocks_needed):
                blocks.append(self.allocate_block())
        except Exception as e:
            for block in blocks:
                self.free_block(block)
            print(f"Failed to write to file {path}: {str(e)}")
            return

        for i in range(num_blocks_needed - 1):
            # 链接各个块
            self.fat[blocks[i]] = blocks[i + 1]
        self.fat[blocks[-1]] = -1

        fcb.address = blocks[0]
        fcb.size = current_size

        index = 0
        block = fcb.address
        while block != -1 and index < current_size:
            end = min(index + self.block_size, current_size)
            # 确保不超出数据的总大小 current_size。
            self.storage[
                block * self.block_size : block * self.block_size + end - index
            ] = data[
                index:end
            ]  # 将当前块的数据写入到文件中。
            index = end
            block = self.fat[block]

        print(f"Data written to file {path}.")
        self.close_file(path)

    def read_file(self, path):
        fcb = self.find_fcb_by_path(path)
        if fcb is None:
            print(f"File {path} not found.")
            return None

        if fcb.is_directory:
            print(f"{path} is a directory, cannot read from it.")
            return None

        if not hasattr(fcb, "is_open") or not fcb.is_open:
            self.open_file(path)

        data = bytearray()
        block = fcb.address
        bytes_left = fcb.size
        while block != -1 and bytes_left > 0:
            bytes_to_read = min(self.block_size, bytes_left)
            data.extend(
                self.storage[
                    block * self.block_size : block * self.block_size + bytes_to_read
                ]
            )  # 将当前块的数据追加到 data 字节数组中。
            bytes_left -= bytes_to_read
            block = self.fat[block]

        try:
            # 去掉末尾的空字节！
            data_str = data.decode("utf-8").rstrip("\x00")
            print(f"Data read from file {path}: {data_str}")
            return data_str
        except (UnicodeDecodeError, Exception) as e:
            print(f"Error decoding data from file {path}: {e}")
            return None
        finally:
            self.close_file(path)

    def list_directory(self):
        for entry in self.current_directory.children:
            print(entry)

    def copy_entry(self, name):
        fcb = self.find_fcb_by_path(name)
        if fcb is None:
            print(f"{name} not found.")
            return

        if fcb.is_directory:
            error_message = "Cannot copy a directory. Only files can be copied."
            print(error_message)
            QMessageBox.warning(None, "Copy Error", error_message)
            return

        self.copied_entry = copy.deepcopy(fcb)
        print(f"Copied {name}.")

    def find_fcb_by_path(self, path):
        # 解析路径，找到文件控制块
        path_parts = path.strip("/").split("/")
        fcb = self.root if path_parts[0] == "root" else self.current_directory
        if path_parts[0] == "root":
            fcb = self.root
            path_parts.pop(0)
        for part in path_parts:
            if fcb.is_directory and part in fcb.children:
                # 进入子目录
                fcb = fcb.children[part]
            else:
                return None
        return fcb

    def paste_entry(self, target_dir_name=None):
        if not self.copied_entry:
            print("No entry to paste.")
            QMessageBox.warning(
                None,
                "Paste Error",
                "There is nothing to paste. Please copy a file or directory first.",
            )
            return

        target_dir = self.current_directory
        if target_dir_name:
            target_dir = self.current_directory.children.get(
                target_dir_name, self.current_directory
            )  # 目标目录可能不存在，则使用当前目录

        if target_dir is None or not target_dir.is_directory:
            print("Invalid target directory.")
            QMessageBox.warning(
                None,
                "Paste Error",
                "The target directory is invalid or not a directory.",
            )
            return

        new_name = self.copied_entry.name
        base_name = new_name
        count = 1
        while new_name in target_dir.children:
            # 重命名文件，使其不与已有文件重名
            new_name = f"{base_name}({count})"
            count += 1

        new_entry = copy.deepcopy(self.copied_entry)
        new_entry.name = new_name
        target_dir.children[new_name] = new_entry
        if new_entry.is_directory:
            # 复制目录时，递归复制其所有子目录和文件
            self._update_fcb_references(new_entry, target_dir)
        print(f"Pasted {new_name}.")

    def _update_fcb_references(self, fcb, parent):
        # 更新文件控制块的父目录引用
        for name, child in fcb.children.items():
            if child.is_directory:
                self._update_fcb_references(child, fcb)
            else:
                parent.children[name] = child
