import unittest
import tempfile
import os
from pathlib import Path
import hashlib
import shutil
from xml.etree.ElementTree import Element, SubElement, ElementTree
from parsergit import GitRepository, read_config

class TestGitRepository(unittest.TestCase):
    def setUp(self):
        """Создание временного репозитория Git для тестов."""
        self.repo_dir = tempfile.mkdtemp()
        self.git_dir = Path(self.repo_dir) / ".git"
        self.objects_dir = self.git_dir / "objects"
        self.git_dir.mkdir()
        self.objects_dir.mkdir(parents=True)

        # Создаем HEAD
        self.head_path = self.git_dir / "HEAD"
        self.head_path.write_text("ref: refs/heads/main")

        # Создаем refs/heads/main
        refs_dir = self.git_dir / "refs" / "heads"
        refs_dir.mkdir(parents=True)
        self.main_ref = refs_dir / "main"

    def tearDown(self):
        """Удаление временного репозитория после тестов."""
        shutil.rmtree(self.repo_dir)

    def test_read_head(self):
        """Тест чтения HEAD."""
        # Устанавливаем HEAD на фиктивный коммит
        test_commit = "1234567890abcdef1234567890abcdef12345678"
        self.main_ref.write_text(test_commit)

        # Проверяем, что HEAD читается правильно
        repo = GitRepository(self.repo_dir, "test.txt")
        self.assertEqual(repo.read_head(), test_commit)

    def test_collect_commits(self):
        """Тест сбора коммитов."""
        # Создаем фиктивный коммит
        commit_hash = self.create_commit("Initial commit", None)
        self.main_ref.write_text(commit_hash)

        # Считываем коммиты
        repo = GitRepository(self.repo_dir, "test.txt")
        repo.collect_commits()

        # Проверяем, что коммит был собран
        self.assertIn(commit_hash, repo.commits)
        self.assertEqual(repo.commits[commit_hash]["author"], "Test User")

    def test_filter_commits_by_file(self):
        """Тест фильтрации коммитов по имени файла."""
        # Создаем коммит, содержащий файл "test.txt"
        blob_hash = self.create_blob("Hello, World!")
        tree_hash = self.create_tree([("100644", "test.txt", blob_hash)])
        commit_hash = self.create_commit("Added test.txt", tree_hash)
        self.main_ref.write_text(commit_hash)

        # Считываем и фильтруем коммиты
        repo = GitRepository(self.repo_dir, "test.txt")
        repo.collect_commits()
        repo.filter_commits_by_file()

        # Проверяем, что коммит остался после фильтрации
        self.assertIn(commit_hash, repo.commits)

    def test_generate_mermaid(self):
        """Тест генерации Mermaid-графа."""
        # Создаем два связанных коммита
        commit1_hash = self.create_commit("First commit", None)
        commit2_hash = self.create_commit("Second commit", commit1_hash)
        self.main_ref.write_text(commit2_hash)

        # Считываем коммиты
        repo = GitRepository(self.repo_dir, "test.txt")
        repo.collect_commits()

        # Генерируем граф
        graph = repo.generate_mermaid()

        # Проверяем наличие узлов и связи
        self.assertIn(commit1_hash, graph)
        self.assertIn(commit2_hash, graph)
        self.assertIn(f"{commit2_hash} --> {commit1_hash}", graph)

    def create_blob(self, content):
        """Создает объект blob."""
        blob_hash = self.create_git_object("blob", content)
        return blob_hash

    def create_tree(self, entries):
        """Создает объект tree."""
        content = "\n".join(f"{mode} {name}\0{hash_}" for mode, name, hash_ in entries)
        tree_hash = self.create_git_object("tree", content)
        return tree_hash

    def create_commit(self, message, parent_hash):
        """Создает объект commit."""
        content = (
            f"tree fake_tree_hash\n"
            f"{f'parent {parent_hash}\n' if parent_hash else ''}"
            f"author Test User <test@example.com> 1234567890 +0000\n"
            f"committer Test User <test@example.com> 1234567890 +0000\n\n"
            f"{message}"
        )
        commit_hash = self.create_git_object("commit", content)
        return commit_hash

    def create_git_object(self, obj_type, content):
        """Создает объект Git и сохраняет его в objects/."""
        import zlib

        header = f"{obj_type} {len(content)}\0"
        data = header + content
        obj_hash = hashlib.sha1(data.encode()).hexdigest()
        obj_path = self.objects_dir / obj_hash[:2] / obj_hash[2:]
        obj_path.parent.mkdir(parents=True, exist_ok=True)

        with open(obj_path, "wb") as f:
            f.write(zlib.compress(data.encode()))

        return obj_hash


class TestConfigReader(unittest.TestCase):
    def test_read_config(self):
        """Тест чтения конфигурации из XML."""
        # Создаем временный XML-файл конфигурации
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xml") as tmp:
            config_path = tmp.name
            root = Element("config")
            SubElement(root, "visualizerPath").text = "/path/to/visualizer"
            SubElement(root, "repositoryPath").text = "/path/to/repo"
            SubElement(root, "targetFile").text = "example.txt"
            tree = ElementTree(root)
            tree.write(config_path)

        # Проверяем, что конфигурация читается правильно
        visualizer_path, repo_path, target_file = read_config(config_path)
        self.assertEqual(visualizer_path, "/path/to/visualizer")
        self.assertEqual(repo_path, "/path/to/repo")
        self.assertEqual(target_file, "example.txt")

        # Удаляем временный файл
        os.remove(config_path)


if __name__ == "__main__":
    unittest.main()
