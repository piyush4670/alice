import json
from pathlib import Path

from ai.extractor import extract

from core.response import success, error


TODO_FILE = Path("data/todos.json")


def load_tasks():

    if not TODO_FILE.exists():
        return []

    try:
        with open(TODO_FILE, "r") as file:
            return json.load(file)
    except Exception:
        return []


def save_tasks(tasks):

    TODO_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(TODO_FILE, "w") as file:
        json.dump(
            tasks,
            file,
            indent=4,
        )


def add(task: str):

    task = task.strip()

    tasks = load_tasks()

    for existing in tasks:

        if existing["task"] == task:
            return False

    tasks.append(
        {
            "task": task,
            "completed": False,
        }
    )

    save_tasks(tasks)

    return True


def list_all():

    tasks = load_tasks()

    return success(
        tasks,
        source="todo",
        data=tasks,
    )


def complete(index):

    tasks = load_tasks()

    if index < 0 or index >= len(tasks):
        return error(
            "Task not found.",
            source="todo",
        )

    if tasks[index]["completed"]:
        return success(
            "That task is already completed.",
            source="todo",
        )

    tasks[index]["completed"] = True

    save_tasks(tasks)

    return success(
        "Task marked as completed.",
        source="todo",
    )


def remove(index):

    tasks = load_tasks()

    if index < 0 or index >= len(tasks):
        return error(
            "Task not found.",
            source="todo",
        )

    removed = tasks.pop(index)

    save_tasks(tasks)

    return success(
        f"Removed task: {removed['task']}",
        source="todo",
    )


def handle(message: str):

    data = extract(message)

    if data is None:
        return error(
            "I couldn't understand that task request.",
            source="todo",
        )

    if data["intent"] == "todo_add":

        if add(data["task"]):

            return success(
                "Task added.",
                source="todo",
            )

        return success(
            "That task already exists.",
            source="todo",
        )

    if data["intent"] == "todo_list":

        tasks = list_all()

        if not tasks.data:

            return success(
                "You don't have any tasks.",
                source="todo",
            )

        lines = []

        for index, task in enumerate(tasks.data, start=1):

            mark = "✓" if task["completed"] else " "

            lines.append(
                f"{index}. [{mark}] {task['task']}"
            )

        return success(
            "\n".join(lines),
            source="todo",
        )

    if data["intent"] == "todo_complete":

        return complete(data["index"])

    if data["intent"] == "todo_delete":

        return remove(data["index"])

    return error(
        "Unknown task operation.",
        source="todo",
    )
