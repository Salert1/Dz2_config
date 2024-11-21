import argparse
import subprocess
import os
import xml.etree.ElementTree as ET
from graphviz import Digraph


def parse_config(config_path):
    """Парсит XML конфигурационный файл."""
    tree = ET.parse(config_path)
    root = tree.getroot()
    config = {
        'visualizer_path': root.find('visualizer_path').text,
        'repository_path': root.find('repository_path').text,
        'target_file': root.find('target_file').text,
    }
    return config


def get_git_commits(repo_path, target_file):
    """Получает список коммитов, затрагивающих заданный файл."""
    os.chdir(repo_path)
    result = subprocess.run(
        ['git', 'log', '--pretty=format:%H|%an|%ad', '--date=iso', '--', target_file],
        stdout=subprocess.PIPE,
        text=True,
        check=True
    )
    commits = []
    for line in result.stdout.splitlines():
        commit_hash, author, date = line.split('|', 2)
        commits.append({'hash': commit_hash, 'author': author, 'date': date})
    return commits


def build_graph(commits):
    """Строит граф в формате Mermaid."""
    dot = Digraph(comment='Dependency Graph')
    for commit in commits:
        node_id = commit['hash'][:7]  # Сокращенный hash для узла
        label = f"{commit['date']}\n{commit['author']}"
        dot.node(node_id, label)

    for i in range(len(commits) - 1):
        dot.edge(commits[i + 1]['hash'][:7], commits[i]['hash'][:7])

    return dot


def visualize_graph(graph, output_path, visualizer_path):
    """Сохраняет и визуализирует граф."""
    graph.render(output_path, format='png', cleanup=True)
    subprocess.run([visualizer_path, f"{output_path}.png"], check=True)


def main():
    parser = argparse.ArgumentParser(description="Генератор графа зависимостей Git.")
    parser.add_argument('config', type=str, help="config.xml")
    args = parser.parse_args()

    # Чтение конфигурации
    config = parse_config(args.config)
    repo_path = config['repository_path']
    target_file = config['target_file']
    visualizer_path = config['visualizer_path']

    # Получение данных о коммитах
    commits = get_git_commits(repo_path, target_file)

    # Построение графа
    graph = build_graph(commits)

    # Визуализация графа
    visualize_graph(graph, 'dependency_graph', visualizer_path)


if __name__ == '__main__':
    main()
