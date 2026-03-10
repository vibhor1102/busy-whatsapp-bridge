import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def read_json(path: Path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    baileys_pkg = read_json(ROOT / "baileys-server" / "package.json")
    baileys_lock = read_json(ROOT / "baileys-server" / "package-lock.json")
    dashboard_pkg = read_json(ROOT / "dashboard-react" / "package.json")

    report = {
        "baileys_bridge": {
            "declared": baileys_pkg.get("dependencies", {}),
            "installed_root": baileys_lock.get("packages", {}).get("", {}).get("dependencies", {}),
        },
        "dashboard": {
            "declared": dashboard_pkg.get("dependencies", {}),
        },
        "python_requirements": (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines(),
    }

    out_path = ROOT / "dependency-audit-report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Dependency audit written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
