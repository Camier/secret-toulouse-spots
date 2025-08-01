
// Additional layer controls for relevance filtering
const relevanceLayers = {
    high: L.layerGroup(),
    'medium-high': L.layerGroup(),
    medium: L.layerGroup(),
    low: L.layerGroup()
};

// Add relevance filter UI
function addRelevanceFilters() {
    const relevanceSection = `
        <div class="mb-4">
            <h4 class="text-sm font-semibold text-gray-600 mb-2">
                <i class="fas fa-star mr-1"></i> Pertinence
            </h4>
            <div class="space-y-1">
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" checked data-relevance="high">
                    <span>🌟 Incontournables</span>
                </label>
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" checked data-relevance="medium-high">
                    <span>⭐ Très intéressants</span>
                </label>
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" checked data-relevance="medium">
                    <span>📍 Intéressants</span>
                </label>
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" data-relevance="low">
                    <span>🔍 À explorer</span>
                </label>
            </div>
        </div>
        
        <div class="mb-4">
            <h4 class="text-sm font-semibold text-gray-600 mb-2">
                <i class="fas fa-database mr-1"></i> Sources
            </h4>
            <div class="space-y-1">
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" checked data-source="manual">
                    <span>📝 Contributions</span>
                </label>
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" checked data-source="reddit">
                    <span>💬 Reddit</span>
                </label>
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" checked data-source="tourism">
                    <span>🏛️ Tourisme</span>
                </label>
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" checked data-source="osm">
                    <span>🗺️ OpenStreetMap</span>
                </label>
            </div>
        </div>
    `;
    
    // Insert after existing filters
    document.getElementById('filters').insertAdjacentHTML('beforeend', relevanceSection);
    
    // Add event handlers
    document.querySelectorAll('[data-relevance]').forEach(checkbox => {
        checkbox.addEventListener('change', updateRelevanceLayers);
    });
    
    document.querySelectorAll('[data-source]').forEach(checkbox => {
        checkbox.addEventListener('change', updateSourceLayers);
    });
}

// Update layers based on relevance
function updateRelevanceLayers() {
    // Clear existing markers
    markers.clearLayers();
    
    // Add spots based on active filters
    filteredSpots.forEach(spot => {
        const relevanceCheckbox = document.querySelector(`[data-relevance="${spot.relevance_category}"]`);
        const sourceType = spot.source.includes('osm') ? 'osm' : 
                          spot.source.includes('reddit') ? 'reddit' :
                          spot.source.includes('tourism') ? 'tourism' : 'manual';
        const sourceCheckbox = document.querySelector(`[data-source="${sourceType}"]`);
        
        if (relevanceCheckbox?.checked && sourceCheckbox?.checked) {
            // Add marker with relevance styling
            const marker = createRelevanceMarker(spot);
            markers.addLayer(marker);
        }
    });
}

// Create marker with relevance-based styling
function createRelevanceMarker(spot) {
    const type = spotTypes[spot.type] || spotTypes.unknown;
    let iconSize = [32, 32];
    let opacity = 1;
    
    // Adjust marker based on relevance
    switch(spot.relevance_category) {
        case 'high':
            iconSize = [36, 36];
            break;
        case 'medium-high':
            iconSize = [32, 32];
            break;
        case 'medium':
            iconSize = [28, 28];
            opacity = 0.9;
            break;
        case 'low':
            iconSize = [24, 24];
            opacity = 0.7;
            break;
    }
    
    const icon = L.divIcon({
        html: `<div class="spot-marker" style="opacity: ${opacity}; font-size: ${iconSize[0]}px;">
                ${type.icon}
               </div>`,
        className: 'custom-div-icon',
        iconSize: iconSize,
        iconAnchor: [iconSize[0]/2, iconSize[1]/2]
    });
    
    const marker = L.marker([spot.latitude, spot.longitude], { icon });
    
    // Enhanced popup with relevance info
    const popupContent = `
        ${createPopup(spot)}
        <div class="mt-2 pt-2 border-t">
            <span class="text-xs">${spot.relevance_label}</span>
        </div>
    `;
    
    marker.bindPopup(popupContent);
    return marker;
}
