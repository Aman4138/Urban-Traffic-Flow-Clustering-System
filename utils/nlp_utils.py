class TrafficNLP:
    """Generate traffic summaries"""
    
    def __init__(self):
        """Initialize NLP module"""
        print("✓ NLP module initialized")
    
    def generate_summary(self, density_score, bbox_count, cluster_level):
        """Generate detailed summary"""
        
        # Traffic condition
        if cluster_level == "low":
            condition = "Light Traffic"
            emoji = "🟢"
        elif cluster_level == "medium":
            condition = "Moderate Traffic"
            emoji = "🟡"
        else:
            condition = "Heavy Traffic"
            emoji = "🔴"
        
        # Density percentage
        density_percent = int(density_score * 100)
        
        # Vehicle analysis
        if bbox_count == 0:
            vehicle_desc = "No vehicles detected"
        elif bbox_count <= 3:
            vehicle_desc = f"{bbox_count} vehicle(s) - Very light flow"
        elif bbox_count <= 8:
            vehicle_desc = f"{bbox_count} vehicles - Smooth traffic"
        elif bbox_count <= 15:
            vehicle_desc = f"{bbox_count} vehicles - Moderate congestion"
        else:
            vehicle_desc = f"{bbox_count} vehicles - Heavy congestion"
        
        # Recommendations
        if cluster_level == "low":
            recommendation = "Short green signal recommended"
        elif cluster_level == "medium":
            recommendation = "Balanced signal timing needed"
        else:
            recommendation = "Extended green signal required"
        
        # Build summary
        summary = f"""{emoji} {condition} Detected

📊 Traffic Analysis:
• Density Level: {density_percent}%
• {vehicle_desc}
• Cluster: {cluster_level.upper()}

💡 Recommendation:
{recommendation}

🚦 Status: Active monitoring
"""
        
        return summary.strip()
