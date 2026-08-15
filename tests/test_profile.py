import unittest

from apr.profile import Profile, SkillClaim, TargetSkill, load_profile
from tests import fixture_dir


NEW_FORMAT = """profile:
  name: "修"
  role: "本科生"
  goal:
    - "Java后端开发"
    - "AI项目开发"
skills:
  mastered:
    - name: "Python"
      level: "basic"
      topics:
        - "基础语法"
        - "函数"
  learning:
    - name: "Java"
      level: "beginner"
      topics:
        - "面向对象"
  target:
    - name: "Redis"
      priority: "high"
learning_preferences:
  project_based: true
  prefer_chinese: true
"""

OLD_FORMAT = """name: 修
background: 一句话介绍
known_skills:
  - Python: intermediate
  - Git
learning_goals:
  - 系统设计
"""


class ProfileTest(unittest.TestCase):
    def test_new_format_load(self):
        root = fixture_dir("config")
        (root / "profile.yaml").write_text(NEW_FORMAT, encoding="utf-8")
        p = load_profile(root / "profile.yaml")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "修")
        self.assertEqual(p.role, "本科生")
        self.assertEqual(p.goals, ["Java后端开发", "AI项目开发"])
        self.assertEqual(len(p.mastered), 1)
        self.assertEqual(p.mastered[0].name, "Python")
        self.assertEqual(p.mastered[0].level, "basic")
        self.assertEqual(p.mastered[0].topics, ["基础语法", "函数"])
        self.assertEqual(p.learning[0].name, "Java")
        self.assertEqual(p.targets[0].name, "Redis")
        self.assertEqual(p.targets[0].priority, "high")
        self.assertIs(p.preferences["project_based"], True)
        self.assertFalse(p.is_empty)

    def test_old_format_load(self):
        root = fixture_dir("config")
        (root / "profile.yaml").write_text(OLD_FORMAT, encoding="utf-8")
        p = load_profile(root / "profile.yaml")
        self.assertEqual(p.name, "修")
        self.assertEqual(p.known_skills, ["Python: intermediate", "Git"])
        self.assertEqual(p.learning_goals, ["系统设计"])
        self.assertEqual(p.mastered, [])

    def test_missing_file(self):
        self.assertIsNone(load_profile(fixture_dir("config") / "not-exist.yaml"))

    def test_skill_claim_defaults(self):
        c = SkillClaim()
        self.assertEqual(c.name, "")
        self.assertIsNone(c.level)
        self.assertEqual(c.topics, [])
        t = TargetSkill()
        self.assertEqual(t.priority, "")
        p = Profile()
        self.assertTrue(p.is_empty)
