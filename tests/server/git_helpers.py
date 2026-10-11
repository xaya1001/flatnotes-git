from pathlib import Path

import pygit2


def make_commit(
    repo: pygit2.Repository, filename: str, content: str, message: str
) -> pygit2.Oid:
    (Path(repo.workdir) / filename).write_text(content)
    index = repo.index
    index.add(filename)
    index.write()
    tree_id = index.write_tree()
    author = pygit2.Signature("Helper", "helper@test.com")
    parents = [] if repo.head_is_unborn else [repo.head.target]
    return repo.create_commit("HEAD", author, author, message, tree_id, parents)
