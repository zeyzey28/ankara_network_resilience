from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt


project_dir = Path(__file__).resolve().parent
output_dir = project_dir / "outputs"

results_path = output_dir / "segment_resilience_results.csv"
chart_path = output_dir / "resilience_bar_chart.png"

results = pd.read_csv(results_path)

plt.figure(figsize=(8, 5))
plt.bar(results["rank"], results["percentage_increase"], color="steelblue")
plt.title("Route Distance Increase After Critical Segment Closures")
plt.xlabel("Critical Segment Rank")
plt.ylabel("Distance Increase (%)")
plt.xticks(results["rank"])
plt.tight_layout()
plt.savefig(chart_path, dpi=300)
