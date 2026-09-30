"""
Recommendation Service for SmartWasteX
Provides actionable disposal recommendations, nearest bin mapping,
Green Credit awards, and environmental metric estimations.
"""

CATEGORY_CONFIG = {
    'Biodegradable': {
        'credits': 5,
        'default_bin_id': 'BIN-02',
        'default_bin_location': 'Cafeteria — Biodegradable Bin #02',
        'recommendation': 'Place in the green organic bin. This item will be composted and converted into nutrient-rich soil fertilizer or campus biogas.',
        'co2_saved_kg': 0.45,
        'diverted_weight_kg': 0.25,
        'badge_color': 'success',
        'icon': 'bi-tree-fill'
    },
    'Dry Recyclable': {
        'credits': 10,
        'default_bin_id': 'BIN-01',
        'default_bin_location': 'Main Building — Dry Recyclable Bin #01',
        'recommendation': 'Ensure item is clean and free of liquid contaminants. Deposit in the blue Dry Recyclable bin for mechanical sorting and remanufacturing.',
        'co2_saved_kg': 0.85,
        'diverted_weight_kg': 0.18,
        'badge_color': 'primary',
        'icon': 'bi-recycle'
    },
    'Hazardous / E-Waste': {
        'credits': 25,
        'default_bin_id': 'BIN-04',
        'default_bin_location': 'Engineering Block — E-Waste Bin #04',
        'recommendation': 'Do not place this item in regular waste! Heavy metals and toxic electrolytes require specialized handling at an authorized e-waste collection point.',
        'co2_saved_kg': 2.80,
        'diverted_weight_kg': 0.50,
        'badge_color': 'danger',
        'icon': 'bi-cpu-fill'
    }
}

ITEM_SPECIFIC_RECOMMENDATIONS = {
    'banana peel': {
        'category': 'Biodegradable',
        'recommendation': 'Compost in the green organic bin. Rich in potassium for campus landscaping compost.',
        'bin_id': 'BIN-02',
        'diverted_kg': 0.15
    },
    'food waste': {
        'category': 'Biodegradable',
        'recommendation': 'Deposit in cafeteria wet waste collection for conversion in the campus anaerobic digester.',
        'bin_id': 'BIN-02',
        'diverted_kg': 0.35
    },
    'plastic bottle': {
        'category': 'Dry Recyclable',
        'recommendation': 'Empty liquid, crush flat, and place with caps on in the Dry Recyclable bin.',
        'bin_id': 'BIN-01',
        'diverted_kg': 0.05
    },
    'crushed can': {
        'category': 'Dry Recyclable',
        'recommendation': 'Rinse lightly and place in metal recycling bin. Aluminum is infinitely recyclable.',
        'bin_id': 'BIN-01',
        'diverted_kg': 0.04
    },
    'newspaper': {
        'category': 'Dry Recyclable',
        'recommendation': 'Keep flat and dry. Deposit in paper recycling section at Library collection.',
        'bin_id': 'BIN-03',
        'diverted_kg': 0.20
    },
    'cardboard': {
        'category': 'Dry Recyclable',
        'recommendation': 'Flatten cardboard boxes before placing into the recycling receptacle at Main Building.',
        'bin_id': 'BIN-01',
        'diverted_kg': 0.40
    },
    'battery': {
        'category': 'Hazardous / E-Waste',
        'recommendation': 'Wrap battery terminals with tape if damaged. Hand over at the Engineering Block specialized e-waste collection kiosk.',
        'bin_id': 'BIN-04',
        'diverted_kg': 0.10
    },
    'lithium battery': {
        'category': 'Hazardous / E-Waste',
        'recommendation': 'Handle with care. Do not puncture or expose to heat. Dispose at Engineering Block E-Waste Bin #04.',
        'bin_id': 'BIN-04',
        'diverted_kg': 0.12
    },
    'old smartphone': {
        'category': 'Hazardous / E-Waste',
        'recommendation': 'Perform factory reset to clear personal data. Register in campus E-Waste Tracker for safe precious metal reclamation.',
        'bin_id': 'BIN-04',
        'diverted_kg': 0.18
    },
    'circuit board': {
        'category': 'Hazardous / E-Waste',
        'recommendation': 'Contains lead and copper traces. Must be routed to certified R2 recyclers via Engineering Block Depot.',
        'bin_id': 'BIN-04',
        'diverted_kg': 0.25
    },
    'laptop': {
        'category': 'Hazardous / E-Waste',
        'recommendation': 'Institutional IT hardware must be logged with asset tag into the E-Waste Digital Passport system before disposal.',
        'bin_id': 'BIN-04',
        'diverted_kg': 2.10
    }
}

def get_recommendation_for_category(category, item_name=None):
    """Returns comprehensive recommendation details for a waste category and item."""
    cfg = CATEGORY_CONFIG.get(category, CATEGORY_CONFIG['Dry Recyclable'])
    
    rec_text = cfg['recommendation']
    bin_id = cfg['default_bin_id']
    diverted_kg = cfg['diverted_weight_kg']
    
    if item_name:
        clean_item = item_name.strip().lower()
        for key, item_data in ITEM_SPECIFIC_RECOMMENDATIONS.items():
            if key in clean_item:
                rec_text = item_data['recommendation']
                bin_id = item_data['bin_id']
                diverted_kg = item_data['diverted_kg']
                break
                
    return {
        'recommendation': rec_text,
        'nearest_bin_id': bin_id,
        'credits': cfg['credits'],
        'diverted_weight_kg': diverted_kg,
        'co2_saved_kg': cfg['co2_saved_kg'],
        'badge_color': cfg['badge_color'],
        'icon': cfg['icon']
    }
