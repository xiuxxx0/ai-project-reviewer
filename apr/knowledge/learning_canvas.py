

LEARNING_STATUS_COLOR = {"已掌握": "4", "学习中": "3", "待学习": "1"}
TASK_LEVEL_COLOR = {"high": "1", "medium": "2", "low": "3"}
LEARNING_COL_X = {"do": 320, "tech": 680, "topic": 1040, "task": 1400}
LEARNING_MAX_TECHS = 10
LEARNING_MAX_TOPICS = 20
LEARNING_MAX_TASKS = 10
LEARNING_TOPICS_PER_TECH = 4


def learning_tech_status(graph, name, assessment, blind_spots):
    """技术节点学习状态：已掌握 / 学习中 / 待学习（游戏技能树语义）。"""
    risk = None
    if blind_spots is not None:
        for b in blind_spots.items:
            if b.skill == name:
                risk = b.risk_level
                break
    if risk in ("高风险盲区", "中风险盲区"):
        return "待学习"
    entry = assessment.entries.get(name) if assessment is not None else None
    if entry is not None:
        if entry.final_level in ("advanced", "expert"):
            return "已掌握"
        if entry.claimed_level or entry.final_level == "intermediate":
            return "学习中"
    skill_node = graph.nodes.get("skill:" + name)
    if skill_node is not None and skill_node.properties.get("claimed_level"):
        return "学习中"
    return "待学习"
