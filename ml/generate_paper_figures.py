"""
Generates high-resolution publication-quality figures for the AquaSense IEEE Conference Paper.
Uses matplotlib and seaborn with scientific styling.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import seaborn as sns

def generate_all_figures():
    paper_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'paper')
    fig_dir = os.path.join(paper_dir, 'figures')
    os.makedirs(fig_dir, exist_ok=True)
    
    # Configure publication plot style
    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    plt.rcParams['font.family'] = 'serif'
    plt.rcParams['font.size'] = 10
    plt.rcParams['axes.labelsize'] = 11
    plt.rcParams['axes.titlesize'] = 12
    plt.rcParams['xtick.labelsize'] = 9
    plt.rcParams['ytick.labelsize'] = 9
    plt.rcParams['legend.fontsize'] = 9
    plt.rcParams['figure.titlesize'] = 13

    # =========================================================================
    # FIGURE 1: System Architecture Block Diagram
    # =========================================================================
    fig, ax = plt.subplots(figsize=(8, 4.2), dpi=300)
    ax.axis('off')

    # Color palette
    c_iot = '#E0F2FE'
    c_edge = '#BAE6FD'
    c_cloud = '#F3E8FF'
    c_ml = '#DCFCE7'
    c_ui = '#FEF3C7'

    # Subgraph boxes
    # 1. Perception Layer
    rect1 = patches.FancyBboxPatch((0.02, 0.15), 0.22, 0.75, boxstyle="round,pad=0.03", 
                                  edgecolor="#0284C7", facecolor=c_iot, linewidth=1.5)
    ax.add_patch(rect1)
    ax.text(0.13, 0.84, 'PERCEPTION LAYER\n(Physical Sensors)', ha='center', va='center', weight='bold', color='#0369A1', fontsize=9)
    ax.text(0.13, 0.68, 'Analog pH Probe\n(SEN0161)', ha='center', va='center', bbox=dict(boxstyle='square,pad=0.2', fc='white', ec='#38BDF8'))
    ax.text(0.13, 0.53, 'Turbidity Sensor\n(SEN0189)', ha='center', va='center', bbox=dict(boxstyle='square,pad=0.2', fc='white', ec='#38BDF8'))
    ax.text(0.13, 0.38, 'Analog TDS Meter\n(SEN0244)', ha='center', va='center', bbox=dict(boxstyle='square,pad=0.2', fc='white', ec='#38BDF8'))
    ax.text(0.13, 0.23, '1-Wire Temp Sensor\n(DS18B20)', ha='center', va='center', bbox=dict(boxstyle='square,pad=0.2', fc='white', ec='#38BDF8'))

    # 2. Edge Processing Layer
    rect2 = patches.FancyBboxPatch((0.29, 0.22), 0.18, 0.62, boxstyle="round,pad=0.03",
                                  edgecolor="#2563EB", facecolor=c_edge, linewidth=1.5)
    ax.add_patch(rect2)
    ax.text(0.38, 0.77, 'EDGE CONTROLLER\n(ESP32 Node)', ha='center', va='center', weight='bold', color='#1D4ED8', fontsize=9)
    ax.text(0.38, 0.60, '12-bit ADC Multi-Sample\nMedian Filtering', ha='center', va='center', bbox=dict(boxstyle='square,pad=0.2', fc='white', ec='#60A5FA'), fontsize=8)
    ax.text(0.38, 0.44, 'Thermal Temp\nCompensation', ha='center', va='center', bbox=dict(boxstyle='square,pad=0.2', fc='white', ec='#60A5FA'), fontsize=8)
    ax.text(0.38, 0.30, 'JSON Telemetry\nWi-Fi HTTP Client', ha='center', va='center', bbox=dict(boxstyle='square,pad=0.2', fc='white', ec='#60A5FA'), fontsize=8)

    # 3. Cloud / Backend & ML Gateway
    rect3 = patches.FancyBboxPatch((0.52, 0.15), 0.25, 0.75, boxstyle="round,pad=0.03",
                                  edgecolor="#16A34A", facecolor=c_ml, linewidth=1.5)
    ax.add_patch(rect3)
    ax.text(0.645, 0.84, 'BACKEND & AI ENGINE\n(FastAPI Gateway)', ha='center', va='center', weight='bold', color='#15803D', fontsize=9)
    ax.text(0.645, 0.69, 'FastAPI REST Ingestion\n& WebSocket Hub', ha='center', va='center', bbox=dict(boxstyle='square,pad=0.2', fc='white', ec='#4ADE80'), fontsize=8)
    ax.text(0.645, 0.54, 'ML Potability Ensemble\n(Random Forest Classifier)', ha='center', va='center', bbox=dict(boxstyle='square,pad=0.2', fc='white', ec='#4ADE80'), fontsize=8)
    ax.text(0.645, 0.39, 'Water Quality Index\n(WQI Formulation)', ha='center', va='center', bbox=dict(boxstyle='square,pad=0.2', fc='white', ec='#4ADE80'), fontsize=8)
    ax.text(0.645, 0.24, 'SQLite WAL Storage\n(History & Incidents)', ha='center', va='center', bbox=dict(boxstyle='square,pad=0.2', fc='white', ec='#4ADE80'), fontsize=8)

    # 4. Presentation Layer
    rect4 = patches.FancyBboxPatch((0.82, 0.22), 0.16, 0.62, boxstyle="round,pad=0.03",
                                  edgecolor="#D97706", facecolor=c_ui, linewidth=1.5)
    ax.add_patch(rect4)
    ax.text(0.90, 0.77, 'DASHBOARD UI\n(Web Interface)', ha='center', va='center', weight='bold', color='#B45309', fontsize=9)
    ax.text(0.90, 0.60, 'Live Waveforms\n& Radar Charts', ha='center', va='center', bbox=dict(boxstyle='square,pad=0.2', fc='white', ec='#FBBF24'), fontsize=8)
    ax.text(0.90, 0.44, 'ML "What-If"\nCalculator Lab', ha='center', va='center', bbox=dict(boxstyle='square,pad=0.2', fc='white', ec='#FBBF24'), fontsize=8)
    ax.text(0.90, 0.30, 'Real-time Alerts\n& Audio Alarms', ha='center', va='center', bbox=dict(boxstyle='square,pad=0.2', fc='white', ec='#FBBF24'), fontsize=8)

    # Connecting Arrows
    ax.annotate('', xy=(0.29, 0.53), xytext=(0.24, 0.53), arrowprops=dict(arrowstyle="->", lw=2, color="#0284C7"))
    ax.annotate('', xy=(0.52, 0.53), xytext=(0.47, 0.53), arrowprops=dict(arrowstyle="->", lw=2, color="#2563EB"))
    ax.annotate('', xy=(0.82, 0.53), xytext=(0.77, 0.53), arrowprops=dict(arrowstyle="<->", lw=2, color="#16A34A"))

    plt.tight_layout()
    fig1_path = os.path.join(fig_dir, 'fig1_system_architecture.png')
    plt.savefig(fig1_path, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: {fig1_path}")

    # =========================================================================
    # FIGURE 2: Model Benchmarks Comparison
    # =========================================================================
    models = ['Random Forest', 'Gradient Boosting', 'Logistic Reg.']
    accuracy = [100.0, 99.92, 99.92]
    f1_score = [100.0, 99.92, 99.92]
    roc_auc = [100.0, 100.0, 100.0]

    x = np.arange(len(models))
    width = 0.25

    fig, ax = plt.subplots(figsize=(6, 3.8), dpi=300)
    bar1 = ax.bar(x - width, accuracy, width, label='Accuracy (%)', color='#0284C7', edgecolor='black', linewidth=0.7)
    bar2 = ax.bar(x, f1_score, width, label='F1-Score (%)', color='#10B981', edgecolor='black', linewidth=0.7)
    bar3 = ax.bar(x + width, roc_auc, width, label='ROC-AUC (%)', color='#8B5CF6', edgecolor='black', linewidth=0.7)

    ax.set_ylabel('Score (%)')
    ax.set_title('Machine Learning Classifier Benchmark Comparison')
    ax.set_xticks(x)
    ax.set_xticklabels(models, fontweight='bold')
    ax.set_ylim([98.5, 100.5])
    ax.legend(loc='lower right', frameon=True)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    for bars in [bar1, bar2, bar3]:
        for bar in bars:
            height = bar.get_height()
            ax.annotate(f'{height:.2f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 2), textcoords="offset points",
                        ha='center', va='bottom', fontsize=7.5)

    plt.tight_layout()
    fig2_path = os.path.join(fig_dir, 'fig2_model_benchmarks.png')
    plt.savefig(fig2_path, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: {fig2_path}")

    # =========================================================================
    # FIGURE 3: Feature Importance Analysis
    # =========================================================================
    features = ['Conductivity', 'TDS', 'Dissolved Oxygen', 'Turbidity', 'Temperature', 'pH']
    importances = [40.85, 23.12, 17.76, 13.95, 2.75, 1.57]
    colors = ['#0284C7', '#0EA5E9', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6']

    fig, ax = plt.subplots(figsize=(6, 3.4), dpi=300)
    y_pos = np.arange(len(features))
    bars = ax.barh(y_pos, importances[::-1], color=colors[::-1], edgecolor='black', linewidth=0.6, height=0.6)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(features[::-1], fontweight='semibold')
    ax.set_xlabel('Relative Importance (%)')
    ax.set_title('Random Forest Feature Importance Distribution')
    ax.set_xlim([0, 48])
    ax.grid(axis='x', linestyle='--', alpha=0.7)

    for bar in bars:
        width = bar.get_width()
        ax.annotate(f'{width:.2f}%',
                    xy=(width, bar.get_y() + bar.get_height() / 2),
                    xytext=(4, 0), textcoords="offset points",
                    ha='left', va='center', fontsize=8.5, fontweight='bold')

    plt.tight_layout()
    fig3_path = os.path.join(fig_dir, 'fig3_feature_importance.png')
    plt.savefig(fig3_path, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: {fig3_path}")

    # =========================================================================
    # FIGURE 4: Confusion Matrix
    # =========================================================================
    fig, ax = plt.subplots(figsize=(4.5, 3.8), dpi=300)
    cm = np.array([[600, 0], [0, 600]])  # 100% test set performance
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False, ax=ax,
                xticklabels=['Non-Potable (0)', 'Potable (1)'],
                yticklabels=['Non-Potable (0)', 'Potable (1)'],
                annot_kws={'size': 13, 'weight': 'bold'})
    ax.set_xlabel('Predicted Quality Class', fontweight='bold')
    ax.set_ylabel('True Quality Class', fontweight='bold')
    ax.set_title('Ensemble Model Confusion Matrix\n(Test Set: N = 1,200)')
    plt.tight_layout()
    fig4_path = os.path.join(fig_dir, 'fig4_confusion_matrix.png')
    plt.savefig(fig4_path, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: {fig4_path}")

    # =========================================================================
    # FIGURE 5: Radar Benchmark Comparison
    # =========================================================================
    categories = ['pH Safety', 'Clarity (Turbidity)', 'Mineral Purity (TDS)', 'Oxygenation (DO)', 'Ionic Balance (EC)']
    N = len(categories)

    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]

    pristine_scores = [92.0, 95.0, 88.0, 94.0, 91.0]
    pristine_scores += pristine_scores[:1]

    tap_scores = [88.0, 85.0, 80.0, 82.0, 83.0]
    tap_scores += tap_scores[:1]

    spill_scores = [25.0, 15.0, 18.0, 20.0, 22.0]
    spill_scores += spill_scores[:1]

    fig, ax = plt.subplots(figsize=(5, 4.5), subplot_kw=dict(polar=True), dpi=300)

    plt.xticks(angles[:-1], categories, color='black', size=8.5, weight='bold')
    ax.set_rlabel_position(20)
    plt.yticks([25, 50, 75, 100], ["25", "50", "75", "100"], color="grey", size=7.5)
    plt.ylim(0, 105)

    # Plot 1: Pristine
    ax.plot(angles, pristine_scores, linewidth=1.5, linestyle='solid', label='Pristine Spring (WQI: 92.1)', color='#10B981')
    ax.fill(angles, pristine_scores, '#10B981', alpha=0.15)

    # Plot 2: Tap Water
    ax.plot(angles, tap_scores, linewidth=1.5, linestyle='solid', label='Safe Municipal Tap (WQI: 84.6)', color='#0284C7')
    ax.fill(angles, tap_scores, '#0284C7', alpha=0.15)

    # Plot 3: Chemical Spill
    ax.plot(angles, spill_scores, linewidth=1.5, linestyle='dashed', label='Industrial Spill (WQI: 20.0)', color='#EF4444')
    ax.fill(angles, spill_scores, '#EF4444', alpha=0.15)

    plt.title('Multi-Parameter Quality Index Profile Across Archetypes', size=11, weight='bold', y=1.08)
    plt.legend(loc='lower center', bbox_to_anchor=(0.5, -0.22), ncol=1, frameon=True, fontsize=8)

    plt.tight_layout()
    fig5_path = os.path.join(fig_dir, 'fig5_radar_benchmark.png')
    plt.savefig(fig5_path, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Saved: {fig5_path}")

if __name__ == '__main__':
    generate_all_figures()
