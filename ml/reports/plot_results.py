import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Apply a professional, clean style for research papers
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_context("paper", font_scale=1.4)

def load_data(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def plot_feature_importance(features, title, filename, color):
    # Sort features by importance
    features.sort(key=lambda x: x['importance'], reverse=False)
    
    names = [f['feature'].replace('_', ' ').title() for f in features]
    importances = [f['importance'] * 100 for f in features]  # Convert to percentage
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(names, importances, color=color, edgecolor='black', alpha=0.8)
    
    # Add values at the end of the bars
    for bar in bars:
        width = bar.get_width()
        ax.annotate(f'{width:.1f}%',
                    xy=(width, bar.get_y() + bar.get_height() / 2),
                    xytext=(3, 0),  # 3 points horizontal offset
                    textcoords="offset points",
                    ha='left', va='center',
                    fontsize=11)
    
    ax.set_xlabel('Relative Importance (%)', fontweight='bold')
    ax.set_title(title, fontweight='bold', pad=15)
    ax.set_xlim(0, max(importances) * 1.15)  # Add space for labels
    
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()

def plot_model_metrics(data, filename):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    
    # Cost & Delay Model Performance
    ax1 = axes[0]
    metrics = ['R2 Score', 'MAE']
    
    cost_r2 = data['models']['cost_overrun']['r2']
    delay_r2 = data['models']['delay']['r2']
    
    cost_mae = data['models']['cost_overrun']['mae']
    delay_mae = data['models']['delay']['mae']
    
    x = np.arange(len(metrics))
    width = 0.35
    
    # Scale R2 by 10 for visualization alongside MAE, or use twin axes
    ax1.bar(x - width/2, [cost_r2 * 10, cost_mae], width, label='Cost Overrun', color='#2ecc71', edgecolor='black')
    ax1.bar(x + width/2, [delay_r2 * 10, delay_mae], width, label='Delay Prediction', color='#e74c3c', edgecolor='black')
    
    ax1.set_ylabel('Scores')
    ax1.set_title('Regression Models Performance', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(['R2 Score (x10)', 'MAE (%)'])
    ax1.legend()
    
    # Risk Classifier Performance
    ax2 = axes[1]
    risk_acc = data['models']['risk_classifier']['accuracy'] * 100
    risk_f1 = data['models']['risk_classifier']['f1_weighted'] * 100
    
    ax2.bar(['Accuracy', 'Weighted F1'], [risk_acc, risk_f1], color=['#3498db', '#9b59b6'], edgecolor='black', width=0.5)
    
    for i, v in enumerate([risk_acc, risk_f1]):
        ax2.text(i, v + 2, f"{v:.1f}%", ha='center', fontweight='bold')
        
    ax2.set_ylabel('Percentage (%)')
    ax2.set_title('Risk Classifier Performance', fontweight='bold')
    ax2.set_ylim(0, 100)
    
    plt.tight_layout()
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.close()

if __name__ == "__main__":
    report_path = 'training_report.json'
    data = load_data(report_path)
    
    # Generate Feature Importance Plots
    plot_feature_importance(data['feature_importance']['cost'], 
                          'Top 10 Feature Importances: Cost Overrun Model', 
                          'plots/cost_feature_importance.png', 
                          '#2ecc71')
                          
    plot_feature_importance(data['feature_importance']['delay'], 
                          'Top 10 Feature Importances: Delay Prediction Model', 
                          'plots/delay_feature_importance.png', 
                          '#e74c3c')
                          
    plot_feature_importance(data['feature_importance']['risk'], 
                          'Top 10 Feature Importances: Risk Classification Model', 
                          'plots/risk_feature_importance.png', 
                          '#3498db')
                          
    # Generate Combined Metrics Plot
    plot_model_metrics(data, 'plots/model_performance_metrics.png')
    
    print("Plots generated successfully in 'plots' directory.")
