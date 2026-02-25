import numpy as np

class TrafficClusterer:
    """Simple rule-based traffic clustering"""
    
    def __init__(self):
        """Initialize clusterer"""
        # print("✓ Traffic clusterer initialized")
        pass
    
    def predict_cluster(self, density_score):
        """
        Predict traffic cluster
        Returns: (cluster_label, cluster_name)
        """
        try:
            # Simple rule-based clustering
            if density_score < 0.35:
                return 0, "low"
            elif density_score < 0.70:
                return 1, "medium"
            else:
                return 2, "high"
                
        except Exception as e:
            print(f"Clustering error: {e}")
            return 1, "medium"
