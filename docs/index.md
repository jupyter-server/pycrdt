Pycrdt is a Python CRDT library that provides bindings for [Yrs](https://github.com/y-crdt/y-crdt/tree/main/yrs), the Rust port of the [Yjs framework](https://yjs.dev).

Conflict-free Replicated Data Types (CRDTs) allow creating shared documents that can automatically merge changes made concurrently on different "copies" of the data. When the data lives on different machines, they make it possible to build distributed systems that work with local data, leaving the synchronization and conflict resolution with remote data to the CRDT algorithm, which ensures that all data replicas eventually converge to the same state.

Pycrdt is an alternative to [Ypy](https://ypy.readthedocs.io/). Their architectures differ in that pycrdt is a mixed Python/Rust project, while ypy is Rust-only. This probably gives ypy a performance gain, at the cost of complexity. Pycrdt is more Pythonic and its code base probably easier to understand and maintain. For more information, see the following GitHub issues:

- [Move pycrdt to jupyter-server](https://github.com/jupyter-server/team-compass/issues/55)
- [New Python bindings for Yrs](https://github.com/y-crdt/ypy/issues/146)
