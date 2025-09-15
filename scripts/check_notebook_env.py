"""
Quick sanity check for notebook tooling installed via Poetry.
Prints versions of key packages used by the new Notebook Interface.
"""

def main() -> None:
    def safe_import(name: str):
        try:
            mod = __import__(name)
            ver = getattr(mod, "__version__", "<no __version__>")
            print(f"{name}: {ver}")
        except Exception as e:
            print(f"{name}: MISSING ({e})")

    print("Notebook tooling versions:")
    for pkg in [
        "jupyter",
        "ipykernel",
        "jupytext",
        "papermill",
        "nbclient",
        "nbconvert",
        "nbformat",
        "ipywidgets",
    ]:
        safe_import(pkg)


if __name__ == "__main__":
    main()

