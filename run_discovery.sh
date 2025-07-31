#!/bin/bash
# Run complete hidden spots discovery pipeline

echo "🗺️ Starting Hidden Spots Discovery Pipeline"
echo "=========================================="

# Change to scrapers directory
cd scrapers

# Setup database if not exists
if [ ! -f "../hidden_spots.db" ]; then
    echo "📊 Setting up database..."
    python setup_database.py
fi

# Run all scrapers
echo -e "\n🕷️ Running scrapers..."
python main_scraper.py

# Generate report
echo -e "\n📝 Generating comprehensive report..."
python generate_comprehensive_report.py

# Move outputs to root
echo -e "\n📁 Moving outputs..."
mv hidden_spots.db ../ 2>/dev/null || true
mv hidden_spots_export.json ../ 2>/dev/null || true
mv spots_coordinates.csv ../ 2>/dev/null || true

# Create visualization
echo -e "\n🗺️ Creating map visualization..."
python visualize_toulouse_spots.py

echo -e "\n✅ Discovery pipeline complete!"
echo "Check hidden_spots_export.json for results"