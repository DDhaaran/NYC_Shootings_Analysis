#!/usr/bin/env python3
"""
NYC Shootings Cluster Analysis - Complete Pipeline
Generates comprehensive visualizations and analysis outputs
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import folium
from folium.plugins import HeatMap, MarkerCluster
import plotly.graph_objects as go
import plotly.express as px
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Set styles
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)
plt.rcParams['font.size'] = 10

print("\n" + "="*80)
print("NYC SHOOTINGS CLUSTER ANALYSIS - COMPLETE PIPELINE")
print("="*80)

# ============================================================================
# 1. DATA LOADING
# ============================================================================
print("\n[1/7] LOADING DATA...")
df = pd.read_csv('NYPD_Shooting_Incident_Data__Historic_.csv')
print(f"✓ Loaded {len(df):,} incidents")
print(f"✓ Date range: {df['OCCUR_DATE'].min()} to {df['OCCUR_DATE'].max()}")

# ============================================================================
# 2. DATA PREPROCESSING
# ============================================================================
print("\n[2/7] DATA PREPROCESSING...")

# Convert date columns
df['OCCUR_DATE'] = pd.to_datetime(df['OCCUR_DATE'], format='%m/%d/%Y')
df['OCCUR_TIME'] = pd.to_datetime(df['OCCUR_TIME'], format='%H:%M:%S').dt.time
df['Hour'] = pd.to_datetime(df['OCCUR_TIME'], format='%H:%M:%S').dt.hour

# Remove rows with missing coordinates
df_clean = df[df['Latitude'].notna() & df['Longitude'].notna()].copy()
print(f"✓ Retained {len(df_clean):,} incidents with coordinates ({len(df_clean)/len(df)*100:.1f}%)")

# Create temporal features
df_clean['Year'] = df_clean['OCCUR_DATE'].dt.year
df_clean['Month'] = df_clean['OCCUR_DATE'].dt.month
df_clean['DayOfWeek'] = df_clean['OCCUR_DATE'].dt.dayofweek
df_clean['Week'] = df_clean['OCCUR_DATE'].dt.isocalendar().week
df_clean['Quarter'] = df_clean['OCCUR_DATE'].dt.quarter

# Fill missing values
df_clean['PERP_AGE_GROUP'].fillna('UNKNOWN', inplace=True)
df_clean['PERP_SEX'].fillna('U', inplace=True)
df_clean['PERP_RACE'].fillna('UNKNOWN', inplace=True)
df_clean['LOC_CLASSFCTN_DESC'].fillna('UNKNOWN', inplace=True)

print("✓ Temporal features engineered")
print("✓ Missing values handled")

# ============================================================================
# 3. FEATURE ENGINEERING
# ============================================================================
print("\n[3/7] FEATURE ENGINEERING...")

# Encode categorical variables
le_boro = LabelEncoder()
le_perp_race = LabelEncoder()
le_perp_sex = LabelEncoder()
le_vic_race = LabelEncoder()
le_vic_sex = LabelEncoder()
le_vic_age = LabelEncoder()
le_loc = LabelEncoder()

df_clean['BORO_ENCODED'] = le_boro.fit_transform(df_clean['BORO'])
df_clean['PERP_RACE_ENCODED'] = le_perp_race.fit_transform(df_clean['PERP_RACE'])
df_clean['PERP_SEX_ENCODED'] = le_perp_sex.fit_transform(df_clean['PERP_SEX'])
df_clean['VIC_RACE_ENCODED'] = le_vic_race.fit_transform(df_clean['VIC_RACE'])
df_clean['VIC_SEX_ENCODED'] = le_vic_sex.fit_transform(df_clean['VIC_SEX'])
df_clean['VIC_AGE_ENCODED'] = le_vic_age.fit_transform(df_clean['VIC_AGE_GROUP'])
df_clean['LOC_ENCODED'] = le_loc.fit_transform(df_clean['LOC_CLASSFCTN_DESC'])

# Murder flag encoding
df_clean['MURDER_FLAG'] = df_clean['STATISTICAL_MURDER_FLAG'].astype(int)

# Select clustering features
clustering_features = [
    'Hour', 'DayOfWeek', 'Month', 'Latitude', 'Longitude',
    'BORO_ENCODED', 'PRECINCT', 'PERP_RACE_ENCODED', 'PERP_SEX_ENCODED',
    'VIC_RACE_ENCODED', 'VIC_SEX_ENCODED', 'VIC_AGE_ENCODED',
    'LOC_ENCODED', 'MURDER_FLAG'
]

X = df_clean[clustering_features].copy()
X_scaled = StandardScaler().fit_transform(X)

print(f"✓ Engineered {len(clustering_features)} features")
print(f"✓ Scaled feature matrix: {X_scaled.shape}")

# ============================================================================
# 4. ALGORITHM COMPARISON
# ============================================================================
print("\n[4/7] COMPARING CLUSTERING ALGORITHMS...")

# Sample for faster comparison
np.random.seed(42)
sample_size = min(5000, len(X_scaled))
sample_indices = np.random.choice(len(X_scaled), sample_size, replace=False)
X_sample = X_scaled[sample_indices]

algorithms = {}
scores = {}

# K-Means
print("  - Testing K-Means...", end=" ")
kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
kmeans.fit(X_sample)
scores['K-Means'] = silhouette_score(X_sample, kmeans.labels_)
print(f"Silhouette: {scores['K-Means']:.4f}")

# DBSCAN
print("  - Testing DBSCAN...", end=" ")
dbscan = DBSCAN(eps=1.5, min_samples=20)
dbscan.fit(X_sample)
n_clusters_dbscan = len(set(dbscan.labels_)) - (1 if -1 in dbscan.labels_ else 0)
if n_clusters_dbscan > 1:
    scores['DBSCAN'] = silhouette_score(X_sample, dbscan.labels_)
else:
    scores['DBSCAN'] = -1
print(f"Silhouette: {scores['DBSCAN']:.4f}, Clusters: {n_clusters_dbscan}")

# Hierarchical Clustering
print("  - Testing Agglomerative...", end=" ")
hc = AgglomerativeClustering(n_clusters=5, linkage='ward')
hc.fit(X_sample)
scores['Agglomerative'] = silhouette_score(X_sample, hc.labels_)
print(f"Silhouette: {scores['Agglomerative']:.4f}")

# Gaussian Mixture
print("  - Testing Gaussian Mixture...", end=" ")
gm = GaussianMixture(n_components=5, random_state=42)
gm.fit(X_sample)
scores['GaussianMixture'] = silhouette_score(X_sample, gm.predict(X_sample))
print(f"Silhouette: {scores['GaussianMixture']:.4f}")

best_algo = max(scores, key=scores.get)
print(f"\n✓ Best algorithm: {best_algo} (Silhouette: {scores[best_algo]:.4f})")

# ============================================================================
# 5. OPTIMAL CLUSTERING
# ============================================================================
print("\n[5/7] PERFORMING K-MEANS CLUSTERING...")

# Run K-Means on full dataset with k=5
kmeans_final = KMeans(n_clusters=5, random_state=42, n_init=20)
clusters = kmeans_final.fit_predict(X_scaled)
df_clean['Cluster'] = clusters

# Validation metrics
silhouette = silhouette_score(X_scaled, clusters)
davies_bouldin = davies_bouldin_score(X_scaled, clusters)
calinski_harabasz = calinski_harabasz_score(X_scaled, clusters)

print(f"✓ Clustering complete ({len(set(clusters))} clusters)")
print(f"✓ Silhouette Score: {silhouette:.4f}")
print(f"✓ Davies-Bouldin Index: {davies_bouldin:.4f}")
print(f"✓ Calinski-Harabasz Score: {calinski_harabasz:.1f}")

# Cluster statistics
print("\nCluster Distribution:")
for cluster in sorted(df_clean['Cluster'].unique()):
    count = len(df_clean[df_clean['Cluster'] == cluster])
    pct = count / len(df_clean) * 100
    murder_rate = df_clean[df_clean['Cluster'] == cluster]['MURDER_FLAG'].mean() * 100
    print(f"  Cluster {cluster}: {count:,} incidents ({pct:.1f}%), Murder Rate: {murder_rate:.1f}%")

# ============================================================================
# 6. VISUALIZATIONS
# ============================================================================
print("\n[6/7] GENERATING VISUALIZATIONS...")

# Create output directory
import os
os.makedirs('outputs', exist_ok=True)

# Color palette for clusters
colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
cluster_colors = {i: colors[i % len(colors)] for i in range(5)}

# 1. Elbow Method
print("  - Elbow Method...", end=" ")
inertias = []
silhouette_scores = []
for k in range(2, 11):
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(X_sample)
    inertias.append(km.inertia_)
    silhouette_scores.append(silhouette_score(X_sample, km.labels_))

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
ax1.plot(range(2, 11), inertias, 'bo-', linewidth=2, markersize=8)
ax1.set_xlabel('Number of Clusters (k)', fontsize=12)
ax1.set_ylabel('Inertia', fontsize=12)
ax1.set_title('Elbow Method For Optimal k', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3)

ax2.plot(range(2, 11), silhouette_scores, 'ro-', linewidth=2, markersize=8)
ax2.set_xlabel('Number of Clusters (k)', fontsize=12)
ax2.set_ylabel('Silhouette Score', fontsize=12)
ax2.set_title('Silhouette Score vs Number of Clusters', fontsize=14, fontweight='bold')
ax2.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('outputs/01_elbow_silhouette.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓")

# 2. Geographic Distribution of Clusters
print("  - Geographic Distribution...", end=" ")
fig, ax = plt.subplots(figsize=(14, 10))
for cluster in sorted(df_clean['Cluster'].unique()):
    cluster_data = df_clean[df_clean['Cluster'] == cluster]
    ax.scatter(cluster_data['Longitude'], cluster_data['Latitude'],
              c=cluster_colors[cluster], label=f'Cluster {cluster}',
              alpha=0.5, s=20, edgecolors='none')
ax.set_xlabel('Longitude', fontsize=12)
ax.set_ylabel('Latitude', fontsize=12)
ax.set_title('Geographic Distribution of Shooting Clusters in NYC', fontsize=14, fontweight='bold')
ax.legend(fontsize=11, loc='best')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('outputs/02_geographic_distribution.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓")

# 3. Temporal Patterns
print("  - Temporal Patterns...", end=" ")
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Hour of Day
hour_cluster = pd.crosstab(df_clean['Hour'], df_clean['Cluster'])
hour_cluster.plot(kind='bar', ax=axes[0, 0], color=[cluster_colors[i] for i in range(5)])
axes[0, 0].set_title('Incidents by Hour of Day and Cluster', fontsize=12, fontweight='bold')
axes[0, 0].set_xlabel('Hour of Day')
axes[0, 0].set_ylabel('Count')
axes[0, 0].legend(title='Cluster', fontsize=9)

# Day of Week
day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
dow_cluster = pd.crosstab(df_clean['DayOfWeek'], df_clean['Cluster'])
dow_cluster.index = [day_names[i] for i in dow_cluster.index]
dow_cluster.plot(kind='bar', ax=axes[0, 1], color=[cluster_colors[i] for i in range(5)])
axes[0, 1].set_title('Incidents by Day of Week and Cluster', fontsize=12, fontweight='bold')
axes[0, 1].set_xlabel('Day of Week')
axes[0, 1].set_ylabel('Count')
axes[0, 1].legend(title='Cluster', fontsize=9)

# Month
month_cluster = pd.crosstab(df_clean['Month'], df_clean['Cluster'])
axes[1, 0].bar(month_cluster.index, month_cluster[0], color=cluster_colors[0], label='Cluster 0', alpha=0.7)
axes[1, 0].set_title('Incidents by Month', fontsize=12, fontweight='bold')
axes[1, 0].set_xlabel('Month')
axes[1, 0].set_ylabel('Count')
for cluster in range(1, 5):
    axes[1, 0].bar(month_cluster.index, month_cluster[cluster], bottom=month_cluster.iloc[:, :cluster].sum(axis=1),
                   color=cluster_colors[cluster], label=f'Cluster {cluster}', alpha=0.7)
axes[1, 0].legend(fontsize=9)

# Year trend
year_cluster = pd.crosstab(df_clean['Year'], df_clean['Cluster'])
year_cluster.plot(kind='line', ax=axes[1, 1], marker='o', linewidth=2,
                 color=[cluster_colors[i] for i in range(5)])
axes[1, 1].set_title('Trend by Year', fontsize=12, fontweight='bold')
axes[1, 1].set_xlabel('Year')
axes[1, 1].set_ylabel('Count')
axes[1, 1].legend(title='Cluster', fontsize=9)
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('outputs/03_temporal_patterns.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓")

# 4. Borough Distribution
print("  - Borough Distribution...", end=" ")
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Count by borough and cluster
boro_cluster = pd.crosstab(df_clean['BORO'], df_clean['Cluster'])
boro_cluster.plot(kind='bar', ax=axes[0], color=[cluster_colors[i] for i in range(5)])
axes[0].set_title('Incidents by Borough and Cluster', fontsize=12, fontweight='bold')
axes[0].set_xlabel('Borough')
axes[0].set_ylabel('Count')
axes[0].legend(title='Cluster', fontsize=9)
axes[0].tick_params(axis='x', rotation=45)

# Murder rate by borough and cluster
murder_by_boro = df_clean.groupby(['BORO', 'Cluster'])['MURDER_FLAG'].mean() * 100
murder_pivot = murder_by_boro.unstack()
murder_pivot.plot(kind='bar', ax=axes[1], color=[cluster_colors[i] for i in range(5)])
axes[1].set_title('Murder Rate (%) by Borough and Cluster', fontsize=12, fontweight='bold')
axes[1].set_xlabel('Borough')
axes[1].set_ylabel('Murder Rate (%)')
axes[1].legend(title='Cluster', fontsize=9)
axes[1].tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig('outputs/04_borough_distribution.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓")

# 5. Cluster Characteristics
print("  - Cluster Characteristics...", end=" ")
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Average hour by cluster
cluster_hour = df_clean.groupby('Cluster')['Hour'].mean()
axes[0, 0].bar(cluster_hour.index, cluster_hour.values, color=[cluster_colors[i] for i in cluster_hour.index])
axes[0, 0].set_title('Average Hour of Incident by Cluster', fontsize=12, fontweight='bold')
axes[0, 0].set_xlabel('Cluster')
axes[0, 0].set_ylabel('Average Hour')
axes[0, 0].set_ylim(0, 24)

# Murder rate by cluster
cluster_murder = df_clean.groupby('Cluster')['MURDER_FLAG'].mean() * 100
axes[0, 1].bar(cluster_murder.index, cluster_murder.values, color=[cluster_colors[i] for i in cluster_murder.index])
axes[0, 1].set_title('Murder Rate (%) by Cluster', fontsize=12, fontweight='bold')
axes[0, 1].set_xlabel('Cluster')
axes[0, 1].set_ylabel('Murder Rate (%)')
axes[0, 1].set_ylim(0, 100)

# Average precinct by cluster
cluster_precinct = df_clean.groupby('Cluster')['PRECINCT'].mean()
axes[1, 0].bar(cluster_precinct.index, cluster_precinct.values, color=[cluster_colors[i] for i in cluster_precinct.index])
axes[1, 0].set_title('Average Precinct by Cluster', fontsize=12, fontweight='bold')
axes[1, 0].set_xlabel('Cluster')
axes[1, 0].set_ylabel('Average Precinct')

# Cluster sizes
cluster_sizes = df_clean['Cluster'].value_counts().sort_index()
axes[1, 1].pie(cluster_sizes.values, labels=[f'Cluster {i}' for i in cluster_sizes.index],
              colors=[cluster_colors[i] for i in cluster_sizes.index], autopct='%1.1f%%',
              startangle=90)
axes[1, 1].set_title('Incident Distribution by Cluster', fontsize=12, fontweight='bold')

plt.tight_layout()
plt.savefig('outputs/05_cluster_characteristics.png', dpi=300, bbox_inches='tight')
plt.close()
print("✓")

# 6. Interactive Folium Map
print("  - Interactive Map...", end=" ")
center_lat = df_clean['Latitude'].mean()
center_lon = df_clean['Longitude'].mean()

m = folium.Map(location=[center_lat, center_lon], zoom_start=11)

# Add heatmap layer
heat_data = [[row['Latitude'], row['Longitude']] for idx, row in df_clean.iterrows()]
HeatMap(heat_data, radius=15, blur=25, max_zoom=13).add_to(m)

# Add cluster markers (sample)
sample_data = df_clean.sample(n=min(1000, len(df_clean)), random_state=42)
for idx, row in sample_data.iterrows():
    cluster = row['Cluster']
    folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']],
        radius=3,
        popup=f"Cluster {cluster}",
        color=cluster_colors[cluster],
        fill=True,
        fillColor=cluster_colors[cluster],
        fillOpacity=0.7
    ).add_to(m)

m.save('outputs/06_interactive_map.html')
print("✓")

# ============================================================================
# 7. SUMMARY STATISTICS
# ============================================================================
print("\n[7/7] GENERATING SUMMARY REPORT...")

# Cluster profiles
cluster_profiles = pd.DataFrame()
for cluster in sorted(df_clean['Cluster'].unique()):
    cluster_data = df_clean[df_clean['Cluster'] == cluster]
    cluster_profiles = pd.concat([cluster_profiles, pd.DataFrame({
        'Cluster': [cluster],
        'Count': [len(cluster_data)],
        'Percentage': [f"{len(cluster_data)/len(df_clean)*100:.1f}%"],
        'Avg_Hour': [f"{cluster_data['Hour'].mean():.1f}"],
        'Murder_Rate_%': [f"{cluster_data['MURDER_FLAG'].mean()*100:.1f}%"],
        'Top_Borough': [cluster_data['BORO'].mode()[0]],
        'Top_Day': [cluster_data['DayOfWeek'].mode()[0]],
    })], ignore_index=True)

print("\nCluster Profiles:")
print(cluster_profiles.to_string(index=False))

# Save summary to file
with open('outputs/ANALYSIS_SUMMARY.txt', 'w') as f:
    f.write("="*80 + "\n")
    f.write("NYC SHOOTINGS CLUSTER ANALYSIS - SUMMARY\n")
    f.write("="*80 + "\n\n")
    f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Total Incidents: {len(df_clean):,}\n")
    f.write(f"Analysis Period: {df_clean['OCCUR_DATE'].min().date()} to {df_clean['OCCUR_DATE'].max().date()}\n\n")
    
    f.write("CLUSTERING RESULTS:\n")
    f.write(f"  - Algorithm: K-Means\n")
    f.write(f"  - Number of Clusters: 5\n")
    f.write(f"  - Silhouette Score: {silhouette:.4f}\n")
    f.write(f"  - Davies-Bouldin Index: {davies_bouldin:.4f}\n")
    f.write(f"  - Calinski-Harabasz Score: {calinski_harabasz:.1f}\n\n")
    
    f.write("ALGORITHM COMPARISON:\n")
    for algo, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        f.write(f"  - {algo}: {score:.4f}\n")
    f.write("\n")
    
    f.write("CLUSTER PROFILES:\n")
    f.write(cluster_profiles.to_string(index=False))
    f.write("\n\n")
    
    f.write("FILES GENERATED:\n")
    f.write("  - 01_elbow_silhouette.png: Elbow and Silhouette analysis\n")
    f.write("  - 02_geographic_distribution.png: Spatial distribution of clusters\n")
    f.write("  - 03_temporal_patterns.png: Temporal patterns by hour, day, month, year\n")
    f.write("  - 04_borough_distribution.png: Borough-level analysis\n")
    f.write("  - 05_cluster_characteristics.png: Cluster profiles\n")
    f.write("  - 06_interactive_map.html: Interactive Folium map\n")
    f.write("  - ANALYSIS_SUMMARY.txt: This file\n")

print("\n✓ Summary saved to outputs/ANALYSIS_SUMMARY.txt")

# ============================================================================
# COMPLETION
# ============================================================================
print("\n" + "="*80)
print("✓ ANALYSIS COMPLETE!")
print("="*80)
print("\nGenerated Files:")
import os
for file in sorted(os.listdir('outputs')):
    file_path = os.path.join('outputs', file)
    size = os.path.getsize(file_path) / 1024  # KB
    print(f"  - outputs/{file} ({size:.1f} KB)")
print("\n" + "="*80)
