import os
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path
from subprocess import run
from datetime import datetime


class GitRepository:
    """Класс для работы с существующим репозиторием Git."""

    def __init__(self, repo_path, target_file):
        self.repo_path = Path(repo_path).resolve()
        self.target_file = target_file
        self.objects_path = self.repo_path / ".git" / "objects"
        self.head_path = self.repo_path / ".git" / "HEAD"
        self.commits = {}

        if not (self.repo_path / ".git").exists():
            raise ValueError(f"{repo_path} не является репозиторием Git.")

    def read_head(self):
        """Читает текущую ветку из HEAD."""
        with open(self.head_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content.startswith("ref:"):
            ref_path = content.split(" ", 1)[1]
            return (self.repo_path / ".git" / ref_path).read_text(encoding="utf-8").strip()
        return content

    def get_commit(self, commit_hash):
        """Возвращает содержимое коммита по его хэшу."""
        obj_path = self.objects_path / commit_hash[:2] / commit_hash[2:]
        if not obj_path.exists():
            raise FileNotFoundError(f"Объект {commit_hash} не найден.")
        with open(obj_path, "rb") as f:
            raw_data = f.read()

        # Декодируем zlib-упакованные данные
        import zlib
        data = zlib.decompress(raw_data).decode('utf-8')
        obj_type, _, content = data.partition("\0")
        if obj_type != "commit":
            raise ValueError(f"Объект {commit_hash} не является коммитом.")
        return content

    def parse_commit(self, commit_hash):
        """Парсит содержимое коммита и возвращает его детали, включая дату и время."""
        content = self.get_commit(commit_hash)
        lines = content.splitlines()
        tree_hash = None
        parents = []
        author = None
        author_date = None  # Добавим переменную для хранения даты и времени

        for line in lines:
            if line.startswith("tree "):
                tree_hash = line.split(" ", 1)[1]
            elif line.startswith("parent "):
                parents.append(line.split(" ", 1)[1])
            elif line.startswith("author "):
                author_info = line.split(" ", 1)[1]
                author_name, author_email, author_timestamp, author_timezone = author_info.split(" ")
                author_date = datetime.utcfromtimestamp(int(author_timestamp)).strftime('%Y-%m-%d %H:%M:%S')  # Преобразуем timestamp в дату

        return {
            "hash": commit_hash,
            "tree": tree_hash,
            "parents": parents,
            "author": author,
            "date": author_date,  # Добавляем дату и время в данные коммита
        }

    def collect_commits(self):
        """Собирает коммиты начиная с HEAD."""
        head_commit = self.read_head()
        queue = [head_commit]
        visited = set()

        while queue:
            commit_hash = queue.pop()
            if commit_hash in visited:
                continue
            visited.add(commit_hash)

            try:
                commit_data = self.parse_commit(commit_hash)
                self.commits[commit_hash] = commit_data
                queue.extend(commit_data["parents"])
            except Exception as e:
                print(f"Ошибка обработки коммита {commit_hash}: {e}")

    def filter_commits_by_file(self):
        """Фильтрует коммиты, в которых фигурирует указанный файл."""
        filtered_commits = {}
        for commit_hash, commit_data in self.commits.items():
            tree_hash = commit_data["tree"]
            if self.file_in_tree(tree_hash, self.target_file):
                filtered_commits[commit_hash] = commit_data
        self.commits = filtered_commits

    def file_in_tree(self, tree_hash, target_file):
        """Проверяет, содержится ли файл в указанном дереве."""
        tree_path = self.objects_path / tree_hash[:2] / tree_hash[2:]
        if not tree_path.exists():
            return False

        with open(tree_path, "rb") as f:
            import zlib
            data = zlib.decompress(f.read()).decode('utf-8')
        return target_file in data

    def generate_mermaid(self):
        """Генерирует граф зависимостей в формате Mermaid с датой и временем."""
        lines = ["graph TD"]
        for commit_hash, commit_data in self.commits.items():
            for parent in commit_data["parents"]:
                lines.append(f"    {commit_hash} --> {parent}")
            # Вставляем дату и время в блок коммита
            lines.append(f'    {commit_hash}["{commit_hash}\n{commit_data["author"]}\n{commit_data["date"]}"]')
        return "\n".join(lines)


def read_config(config_path):
    """Читает конфигурацию из XML."""
    tree = ET.parse(config_path)
    root = tree.getroot()

    visualizer_path = root.find("visualizerPath").text.strip()
    repo_path = root.find("repositoryPath").text.strip()
    target_file = root.find("targetFile").text.strip()

    return visualizer_path, repo_path, target_file


if __name__ == "__main__":
    # Читаем конфигурацию
    config_path = "config.xml"
    visualizer_path, repo_path, target_file = read_config(config_path)

    # Работаем с репозиторием
    repo = GitRepository(repo_path, target_file)
    repo.collect_commits()
    repo.filter_commits_by_file()
    mermaid_graph = repo.generate_mermaid()

    # Выводим граф
    print("Mermaid Graph:")
    print(mermaid_graph)

    # Вызываем визуализатор
    if visualizer_path:
        mermaid_file = "graph.mmd"
        with open(mermaid_file, "w", encoding="utf-8") as f:
            f.write(mermaid_graph)
        # На Windows важно убедиться, что путь правильный
        run([visualizer_path, mermaid_file], shell=True)
