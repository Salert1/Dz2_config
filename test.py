import unittest
import parsergit
from unittest.mock import patch, MagicMock
import os

class TestDependencyVisualizer(unittest.TestCase):
    def test_parse_config(self):
        config_path = 'test_config.xml'
        with open(config_path, 'w') as f:
            f.write('''
            <config>
                <visualizer_path>/usr/bin/display</visualizer_path>
                <repository_path>/path/to/repository</repository_path>
                <target_file>example.txt</target_file>
            </config>
            ''')
        config = parse_config(config_path)
        self.assertEqual(config['visualizer_path'], '/usr/bin/display')
        self.assertEqual(config['repository_path'], '/path/to/repository')
        self.assertEqual(config['target_file'], 'example.txt')
        os.remove(config_path)

    @patch('subprocess.run')
    def test_get_git_commits(self, mock_run):
        mock_run.return_value.stdout = "abc123|John Doe|2023-01-01 12:00:00\n"
        commits = get_git_commits('/repo', 'example.txt')
        self.assertEqual(len(commits), 1)
        self.assertEqual(commits[0]['hash'], 'abc123')
        self.assertEqual(commits[0]['author'], 'John Doe')
        self.assertEqual(commits[0]['date'], '2023-01-01 12:00:00')

    def test_build_graph(self):
        commits = [
            {'hash': 'abc123', 'author': 'John Doe', 'date': '2023-01-01 12:00:00'},
            {'hash': 'def456', 'author': 'Jane Doe', 'date': '2023-01-02 13:00:00'},
        ]
        graph = build_graph(commits)
        self.assertIn('abc123', graph.source)
        self.assertIn('def456', graph.source)
        self.assertIn('->', graph.source)

if __name__ == '__main__':
    unittest.main()
