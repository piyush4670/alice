from ai.extractor import extract
from core.config import TODO_FILE
from core.response import error, success
from utils.store import load_list, save_list, valid_index


def load_tasks():
    return load_list(TODO_FILE)


def save_tasks(tasks):
    save_list(TODO_FILE, tasks)


def add(task: str) -> bool:

    task = task.strip()

    if not task:
        return False

    tasks = load_tasks()

    for existing in tasks:

        if existing.get("task", "").lower() == task.lower():
            return False

    tasks.append({
        "task": task,
        "completed": False,
    })

    save_tasks(tasks)

    return True


def format_task(index: int, task: dict) -> str:

    mark = "x" if task.get("completed") else " "

    return f"{index}. [{mark}] {task.get('task', 'Unknown')}"


def format_all(tasks) -> str:

    lines = [
        format_task(number, task)
        for number, task in enumerate(tasks, start=1)
    ]

    return "\n".join(lines)


def list_all():
    """Return a printable message plus the structured list in data."""

    tasks = load_tasks()

    if not tasks:
        return success(
            "You don't have any tasks.",
            source="todo",
            data=[],
        )

    return success(
        format_all(tasks),
        source="todo",
        data=tasks,
    )


def complete(index):

    tasks = load_tasks()

    if not valid_index(index, tasks):
        return error(
            "I couldn't find that task.",
            source="todo",
        )

    if tasks[index].get("completed"):
        return success(
            "That task is already completed.",
            source="todo",
        )

    tasks[index]["completed"] = True

    save_tasks(tasks)

    return success(
        f"Task completed: {tasks[index].get('task', 'Unknown')}",
        source="todo",
    )


def remove(index):

    tasks = load_tasks()

    if not valid_index(index, tasks):
        return error(
            "I couldn't find that task.",
            source="todo",
        )

    removed = tasks.pop(index)

    save_tasks(tasks)

    return success(
        f"Removed task: {removed.get('task', 'Unknown')}",
        source="todo",
    )


def handle(message: str, intent: dict = None):

    data = intent if intent is not None else extract(message)

    if data is None:
        return error(
            "I couldn't understand that task request.",
            source="todo",
        )

    name = data.get("intent")

    if name == "todo_add":

        if add(data["task"]):
            return success("Task added.", source="todo")

        return success("That task already exists.", source="todo")

    if name == "todo_list":
        return list_all()

    if name == "todo_complete":
        return complete(data["index"])

    if name == "todo_delete":
        return remove(data["index"])

    return error("Unknown task operation.", source="todo")
