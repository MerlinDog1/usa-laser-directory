// North America Laser Engraving Directory - Main Application

class BusinessDirectory {
    constructor() {
        this.businesses = [];
        this.filteredBusinesses = [];
        this.selectedBusinesses = new Set();
        this.selectedCategories = new Set();
        this.currentView = 'grid';
        this.map = null;
        this.markers = [];
        
        // DOM Elements
        this.searchInput = document.getElementById('searchInput');
        this.clearSearchBtn = document.getElementById('clearSearch');
        this.categoryCheckboxes = document.getElementById('categoryCheckboxes');
        this.countyFilter = document.getElementById('countyFilter');
        this.sortBy = document.getElementById('sortBy');
        this.resetFiltersBtn = document.getElementById('resetFilters');
        this.resultsGrid = document.getElementById('resultsGrid');
        this.resultsList = document.getElementById('resultsList');
        this.mapContainer = document.getElementById('mapContainer');
        this.resultsCount = document.getElementById('resultsCount');
        this.loading = document.getElementById('loading');
        this.noResults = document.getElementById('noResults');
        this.gridViewBtn = document.getElementById('gridView');
        this.listViewBtn = document.getElementById('listView');
        this.mapViewBtn = document.getElementById('mapView');
        this.selectAllBtn = document.getElementById('selectAllBtn');
        this.deselectAllBtn = document.getElementById('deselectAllBtn');
        this.downloadCsvBtn = document.getElementById('downloadCsvBtn');
        this.selectedCountSpan = document.getElementById('selectedCount');
        this.selectAllCatsBtn = document.getElementById('selectAllCats');
        this.clearCatsBtn = document.getElementById('clearCats');
        
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        await this.loadData();
        this.populateCategoryCheckboxes();
        this.populateFilters();
        this.sort();
        this.render();
    }
    
    setupEventListeners() {
        // Search
        if (this.searchInput) {
            this.searchInput.addEventListener('input', () => {
                this.clearSearchBtn.style.display = this.searchInput.value ? 'flex' : 'none';
                this.filter();
            });
        }
        
        if (this.clearSearchBtn) {
            this.clearSearchBtn.addEventListener('click', () => {
                this.searchInput.value = '';
                this.clearSearchBtn.style.display = 'none';
                this.filter();
            });
        }
        
        // Filters
        if (this.countyFilter) {
            this.countyFilter.addEventListener('change', () => this.filter());
        }
        if (this.sortBy) {
            this.sortBy.addEventListener('change', () => {
                this.sort();
                this.render();
            });
        }
        
        // Distributor-only toggle
        const plaquesOnly = document.getElementById('plaquesOnly');
        if (plaquesOnly) {
            plaquesOnly.addEventListener('change', () => this.filter());
        }
        
        // Has email toggle
        const hasEmail = document.getElementById('hasEmail');
        if (hasEmail) {
            hasEmail.addEventListener('change', () => this.filter());
        }

        const showHidden = document.getElementById('showHidden');
        if (showHidden) {
            showHidden.addEventListener('change', () => this.filter());
        }
        
        // Reset
        if (this.resetFiltersBtn) {
            this.resetFiltersBtn.addEventListener('click', () => this.resetFilters());
        }
        
        // View Toggle
        if (this.gridViewBtn) {
            this.gridViewBtn.addEventListener('click', () => this.setView('grid'));
        }
        if (this.listViewBtn) {
            this.listViewBtn.addEventListener('click', () => this.setView('list'));
        }
        if (this.mapViewBtn) {
            this.mapViewBtn.addEventListener('click', () => this.setView('map'));
        }
        
        // Selection Actions
        if (this.selectAllBtn) {
            this.selectAllBtn.addEventListener('click', () => this.selectAll());
        }
        if (this.deselectAllBtn) {
            this.deselectAllBtn.addEventListener('click', () => this.deselectAll());
        }
        if (this.downloadCsvBtn) {
            this.downloadCsvBtn.addEventListener('click', () => this.downloadCsv());
        }
        if (this.selectAllCatsBtn) {
            this.selectAllCatsBtn.addEventListener('click', () => this.selectAllCategories());
        }
        if (this.clearCatsBtn) {
            this.clearCatsBtn.addEventListener('click', () => this.clearCategories());
        }
    }
    
    async loadData() {
        try {
            const dataFile = document.body?.dataset?.dataFile || 'data/directory-data.json';
            const response = await fetch(dataFile);
            this.businesses = await response.json();
            this.filteredBusinesses = this.businesses.filter(b => this.isPublicBusiness(b));
        } catch (error) {
            console.error('Error loading data:', error);
            this.loading.innerHTML = '<p>Error loading directory data. Please refresh.</p>';
        }
    }
    
    populateCategoryCheckboxes() {
        const categories = [...new Set(this.businesses.map(b => b.category))].sort();
        
        this.categoryCheckboxes.innerHTML = categories.map(cat => `
            <label class="category-checkbox">
                <input type="checkbox" value="${this.escapeHtml(cat)}">
                <span>${this.escapeHtml(cat)}</span>
            </label>
        `).join('');
        
        // Add event listeners to new checkboxes
        this.categoryCheckboxes.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            cb.addEventListener('change', () => {
                if (cb.checked) {
                    this.selectedCategories.add(cb.value);
                } else {
                    this.selectedCategories.delete(cb.value);
                }
                this.filter();
            });
        });
    }
    
    populateFilters() {
        // Get unique counties
        const counties = [...new Set(this.businesses.map(b => b.county))].sort();
        
        // Populate county filter
        counties.forEach(county => {
            const option = document.createElement('option');
            option.value = county;
            option.textContent = county;
            this.countyFilter.appendChild(option);
        });
    }
    
    filter() {
        const searchTerm = this.searchInput.value.toLowerCase().trim();
        const county = this.countyFilter.value;
        const distributorOnly = document.getElementById('plaquesOnly')?.checked || false;
        const hasEmailOnly = document.getElementById('hasEmail')?.checked || false;
        const showHidden = document.getElementById('showHidden')?.checked || false;
        
        this.filteredBusinesses = this.businesses.filter(business => {
            const matchesPublication = showHidden || this.isPublicBusiness(business);

            // Search filter
            const matchesSearch = !searchTerm || 
                (business.company && business.company.toLowerCase().includes(searchTerm)) ||
                (business.address && business.address.toLowerCase().includes(searchTerm)) ||
                (business.county && business.county.toLowerCase().includes(searchTerm)) ||
                (business.category && business.category.toLowerCase().includes(searchTerm)) ||
                (business.email && business.email.toLowerCase().includes(searchTerm)) ||
                (business.phone && business.phone.toLowerCase().includes(searchTerm));
            
            // Category filter (multi-select)
            const matchesCategory = this.selectedCategories.size === 0 || 
                this.selectedCategories.has(business.category);
            
            // County filter
            const matchesCounty = !county || business.county === county;
            
            // Distributor filter
            const matchesDistributor = !distributorOnly || business.category === 'Distributor';
            
            // Has email filter
            const matchesEmail = !hasEmailOnly || this.hasValidEmail(business);
            
            return matchesPublication && matchesSearch && matchesCategory && matchesCounty && matchesDistributor && matchesEmail;
        });
        
        this.sort();
        this.render();
    }
    
    selectAllCategories() {
        this.categoryCheckboxes.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            cb.checked = true;
            this.selectedCategories.add(cb.value);
        });
        this.filter();
    }
    
    clearCategories() {
        this.categoryCheckboxes.querySelectorAll('input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
        this.selectedCategories.clear();
        this.filter();
    }
    
    sort() {
        const sortValue = this.sortBy.value;
        
        this.filteredBusinesses.sort((a, b) => {
            switch (sortValue) {
                case 'name-asc':
                    return (a.company || '').localeCompare(b.company || '');
                case 'name-desc':
                    return (b.company || '').localeCompare(a.company || '');
                case 'county-asc':
                    return (a.county || '').localeCompare(b.county || '');
                case 'county-desc':
                    return (b.county || '').localeCompare(a.county || '');
                case 'category-asc':
                    return (a.category || '').localeCompare(b.category || '');
                default:
                    return 0;
            }
        });
    }
    
    resetFilters() {
        this.searchInput.value = '';
        this.clearSearchBtn.style.display = 'none';
        this.countyFilter.value = '';
        this.sortBy.value = 'name-asc';
        const plaquesOnly = document.getElementById('plaquesOnly');
        if (plaquesOnly) plaquesOnly.checked = false;
        const hasEmail = document.getElementById('hasEmail');
        if (hasEmail) hasEmail.checked = false;
        const showHidden = document.getElementById('showHidden');
        if (showHidden) showHidden.checked = false;
        this.clearCategories();
        this.deselectAll();
        this.filteredBusinesses = this.businesses.filter(b => this.isPublicBusiness(b));
        this.sort();
        this.render();
    }
    
    setView(view) {
        this.currentView = view;
        this.gridViewBtn.classList.toggle('active', view === 'grid');
        this.listViewBtn.classList.toggle('active', view === 'list');
        this.mapViewBtn.classList.toggle('active', view === 'map');
        this.resultsGrid.style.display = view === 'grid' ? 'grid' : 'none';
        this.resultsList.style.display = view === 'list' ? 'flex' : 'none';
        this.mapContainer.style.display = view === 'map' ? 'block' : 'none';
        
        if (view === 'map') {
            this.renderMap();
        }
    }
    
    render() {
        this.loading.style.display = 'none';
        
        const count = this.filteredBusinesses.length;
        this.resultsCount.textContent = count.toLocaleString();
        
        if (count === 0) {
            this.noResults.style.display = 'block';
            this.resultsGrid.innerHTML = '';
            this.resultsList.innerHTML = '';
            return;
        }
        
        this.noResults.style.display = 'none';
        this.renderGrid();
        this.renderList();
        
        if (this.currentView === 'map') {
            this.renderMap();
        }
        
        // Update selection UI after rendering
        this.updateSelectionUI();
    }
    
    renderGrid() {
        this.resultsGrid.innerHTML = this.filteredBusinesses.map(business => this.createCardHTML(business)).join('');
        
        // Add event listeners to checkboxes
        this.resultsGrid.querySelectorAll('.business-checkbox').forEach(cb => {
            cb.addEventListener('change', (e) => {
                const id = parseInt(e.target.dataset.id);
                if (e.target.checked) {
                    this.selectedBusinesses.add(id);
                } else {
                    this.selectedBusinesses.delete(id);
                }
                this.updateSelectionUI();
            });
        });
    }
    
    renderList() {
        this.resultsList.innerHTML = this.filteredBusinesses.map(business => this.createListItemHTML(business)).join('');
        
        // Add event listeners to checkboxes
        this.resultsList.querySelectorAll('.business-checkbox').forEach(cb => {
            cb.addEventListener('change', (e) => {
                const id = parseInt(e.target.dataset.id);
                if (e.target.checked) {
                    this.selectedBusinesses.add(id);
                } else {
                    this.selectedBusinesses.delete(id);
                }
                this.updateSelectionUI();
            });
        });
    }
    
    updateSelectionUI() {
        const count = this.selectedBusinesses.size;
        this.selectedCountSpan.textContent = count;
        this.downloadCsvBtn.disabled = count === 0;
        
        // Update all checkbox states
        document.querySelectorAll('.business-checkbox').forEach(cb => {
            const id = parseInt(cb.dataset.id);
            cb.checked = this.selectedBusinesses.has(id);
        });
    }
    
    selectAll() {
        this.filteredBusinesses.forEach(b => this.selectedBusinesses.add(b.id));
        this.updateSelectionUI();
    }
    
    deselectAll() {
        this.selectedBusinesses.clear();
        this.updateSelectionUI();
    }
    
    downloadCsv() {
        const selected = this.businesses.filter(b => this.selectedBusinesses.has(b.id));
        
        if (selected.length === 0) return;
        
        const headers = ['Company', 'Website', 'Email', 'LinkedIn', 'Instagram', 'Phone', 'Address', 'State / Province', 'Category', 'Main Brand', 'Quality', 'Publication Status', 'Contact Status'];
        const rows = selected.map(b => [
            String(b.company || ''),
            String(b.website || ''),
            String(b.email || ''),
            String(b.linkedin || ''),
            String(b.instagram || ''),
            String(b.phone || ''),
            String(b.address || ''),
            String(b.county || b.state || ''),
            String(b.category || ''),
            String(b.mainBrand || ''),
            String(b.quality || 0),
            String(b.publicationStatus || ''),
            String(b.contactStatus || '')
        ]);
        
        const csvContent = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell.replace(/"/g, '""')}"`).join(','))
        ].join('\n');
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `north-america-laser-directory-${new Date().toISOString().split('T')[0]}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
    }
    
    renderMap() {
        // County coordinates (approximate centers)
        const countyCoords = {
            'Alabama': [32.8067, -86.7911],
            'Alaska': [61.3707, -152.4044],
            'Arizona': [33.7298, -111.4312],
            'Arkansas': [34.9697, -92.3731],
            'California': [36.1162, -119.6816],
            'Colorado': [39.0598, -105.3111],
            'Connecticut': [41.5978, -72.7554],
            'Delaware': [39.3185, -75.5071],
            'Florida': [27.7663, -81.6868],
            'Georgia': [33.0406, -83.6431],
            'Hawaii': [21.0943, -157.4983],
            'Idaho': [44.2405, -114.4788],
            'Illinois': [40.3495, -88.9861],
            'Indiana': [39.8494, -86.2583],
            'Iowa': [42.0115, -93.2105],
            'Kansas': [38.5266, -96.7265],
            'Kentucky': [37.6681, -84.6701],
            'Louisiana': [31.1695, -91.8678],
            'Maine': [44.6939, -69.3819],
            'Maryland': [39.0639, -76.8021],
            'Massachusetts': [42.2302, -71.5301],
            'Michigan': [43.3266, -84.5361],
            'Minnesota': [45.6945, -93.9002],
            'Mississippi': [32.7416, -89.6787],
            'Missouri': [38.4561, -92.2884],
            'Montana': [46.9219, -110.4544],
            'Nebraska': [41.1254, -98.2681],
            'Nevada': [38.3135, -117.0554],
            'New Hampshire': [43.4525, -71.5639],
            'New Jersey': [40.2989, -74.5210],
            'New Mexico': [34.8405, -106.2485],
            'New York': [42.1657, -74.9481],
            'North Carolina': [35.6301, -79.8064],
            'North Dakota': [47.5289, -99.7840],
            'Ohio': [40.3888, -82.7649],
            'Oklahoma': [35.5653, -96.9289],
            'Oregon': [44.5720, -122.0709],
            'Pennsylvania': [40.5908, -77.2098],
            'Rhode Island': [41.6809, -71.5118],
            'South Carolina': [33.8569, -80.9450],
            'South Dakota': [44.2998, -99.4388],
            'Tennessee': [35.7478, -86.6923],
            'Texas': [31.0545, -97.5635],
            'Utah': [40.1500, -111.8624],
            'Vermont': [44.0459, -72.7107],
            'Virginia': [37.7693, -78.1700],
            'Washington': [47.4009, -121.4905],
            'West Virginia': [38.4912, -80.9545],
            'Wisconsin': [44.2685, -89.6165],
            'Wyoming': [42.7560, -107.3025],
            'Greater London': [51.5074, -0.1278],
            'Greater Manchester': [53.4808, -2.2426],
            'West Midlands': [52.4862, -1.8904],
            'West Yorkshire': [53.8008, -1.5491],
            'Merseyside': [53.4084, -2.9916],
            'South Yorkshire': [53.3811, -1.4701],
            'Tyne and Wear': [54.9783, -1.6178],
            'Hampshire': [51.0577, -1.3081],
            'Kent': [51.2787, 0.5217],
            'Essex': [51.7343, 0.4691],
            'Lancashire': [53.8175, -2.5556],
            'Surrey': [51.2538, -0.4473],
            'Hertfordshire': [51.8098, -0.2377],
            'Norfolk': [52.6140, 0.8864],
            'Devon': [50.7156, -3.5309],
            'Nottinghamshire': [53.1000, -1.0000],
            'Staffordshire': [52.8793, -2.0572],
            'Suffolk': [52.1872, 0.9708],
            'Oxfordshire': [51.7520, -1.2577],
            'Cambridgeshire': [52.2053, 0.1218],
            'Derbyshire': [53.1000, -1.5000],
            'Leicestershire': [52.6369, -1.1398],
            'Northamptonshire': [52.2405, -0.9027],
            'Warwickshire': [52.2819, -1.5849],
            'Somerset': [51.1051, -2.9262],
            'Dorset': [50.7488, -2.3445],
            'Gloucestershire': [51.8642, -2.2382],
            'Wiltshire': [51.3492, -1.9927],
            'Cheshire': [53.2000, -2.5000],
            'Cornwall': [50.2660, -5.0527],
            'Cumbria': [54.5772, -2.7975],
            'Bristol': [51.4545, -2.5879],
            'East Sussex': [50.9097, 0.2494],
            'West Sussex': [50.9364, -0.4614],
            'Berkshire': [51.4540, -0.9781],
            'Buckinghamshire': [51.8137, -0.8095],
            'Bedfordshire': [52.1356, -0.4667],
            'North Yorkshire': [54.1551, -1.3832],
            'East Riding of Yorkshire': [53.8439, -0.4275],
            'Lincolnshire': [53.2344, -0.5382],
            'Durham': [54.7761, -1.5733],
            'Northumberland': [55.2083, -2.0784],
            'Shropshire': [52.7080, -2.7540],
            'Herefordshire': [52.0765, -2.6544],
            'Worcestershire': [52.1920, -2.2216],
            'Rutland': [52.6583, -0.6396],
            'Isle of Wight': [50.6938, -1.3047],
            'Northern Ireland': [54.6079, -5.9264],
            'Wales': [52.1307, -3.7837],
            'Scotland': [56.4907, -4.2026],
            'Denmark': [56.2639, 9.5018],
            'Sweden': [60.1282, 18.6435],
            'Norway': [60.4720, 8.4689],
            'Finland': [61.9241, 25.7482],
            'Ontario': [50.0000, -85.0000],
            'British Columbia': [53.7267, -127.6476],
            'Alberta': [53.9333, -116.5765],
            'Quebec': [52.9399, -73.5491],
            'Manitoba': [53.7609, -98.8139],
            'Saskatchewan': [52.9399, -106.4509],
            'Nova Scotia': [44.6820, -63.7443],
            'Unidentified': [39.5, -98.35],
        };
        
        if (!this.map) {
            this.map = L.map('map').setView([43.5, -95.0], 4);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(this.map);
        }
        
        // Clear existing markers
        this.markers.forEach(m => this.map.removeLayer(m));
        this.markers = [];
        
        // Count businesses per county
        const countyCounts = {};
        this.filteredBusinesses.forEach(b => {
            countyCounts[b.county] = (countyCounts[b.county] || 0) + 1;
        });
        
        // Add markers for each county
        Object.entries(countyCounts).forEach(([county, count]) => {
            const coords = countyCoords[county];
            if (coords) {
                const marker = L.circleMarker(coords, {
                    radius: Math.min(8 + count * 0.5, 25),
                    fillColor: '#3b82f6',
                    color: '#1e40af',
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.7
                }).addTo(this.map);
                
                marker.bindPopup(`<h4>${county}</h4><p><strong>${count}</strong> businesses</p>`);
                this.markers.push(marker);
            }
        });
        
        // Invalidate size in case container was hidden
        setTimeout(() => this.map.invalidateSize(), 100);
    }
    
    createCardHTML(business) {
        const categoryClass = this.getCategoryClass(business.category);
        const isSelected = this.selectedBusinesses.has(business.id) ? 'checked' : '';
        
        const links = [];
        if (business.website) links.push(this.createLinkHTML(business.website, 'Website', 'globe'));

        const brandFlag = business.mainBrand
            ? `<span class="wayfinding-flag" title="Main represented brand">🏷️ ${this.escapeHtml(business.mainBrand)}</span>`
            : '';
        const hiddenFlag = this.isPublicBusiness(business)
            ? ''
            : `<span class="hidden-flag" title="Hidden from public view">${this.escapeHtml(this.formatStatus(business.contactStatus || 'hidden'))}</span>`;
        if (this.hasValidEmail(business)) links.push(this.createLinkHTML(`mailto:${business.email}`, 'Email', 'mail'));
        if (business.linkedin) links.push(this.createLinkHTML(business.linkedin, 'LinkedIn', 'linkedin'));
        if (business.instagram) links.push(this.createLinkHTML(business.instagram, 'Instagram', 'instagram'));
        
        return `
            <article class="business-card ${isSelected ? 'selected' : ''}">
                <div class="card-header">
                    <label class="select-checkbox">
                        <input type="checkbox" class="business-checkbox" data-id="${business.id}" ${isSelected}>
                        <span class="checkmark"></span>
                    </label>
                    <div class="card-title-area">
                        <h3 class="card-title">${this.escapeHtml(business.company)}</h3>
                        <span class="card-category ${categoryClass}">${this.escapeHtml(business.category)}</span>
                        ${brandFlag}
                        ${hiddenFlag}
                    </div>
                </div>
                <p class="card-county">📍 ${this.escapeHtml(business.county || business.state || '')}</p>
                <div class="card-links">${links.join('')}</div>
                <div class="card-contact">
                    ${business.phone ? `<p>📞 ${this.escapeHtml(business.phone)}</p>` : ''}
                    ${business.address ? `<p>📍 ${this.escapeHtml(business.address)}</p>` : ''}
                </div>
            </article>
        `;
    }
    
    createListItemHTML(business) {
        const categoryClass = this.getCategoryClass(business.category);
        const isSelected = this.selectedBusinesses.has(business.id) ? 'checked' : '';
        
        const links = [];
        if (business.website) links.push(`<a href="${business.website}" target="_blank" class="card-link">🌐 Website</a>`);

        const brandFlag = business.mainBrand
            ? `<span class="wayfinding-flag" title="Main represented brand">🏷️ ${this.escapeHtml(business.mainBrand)}</span>`
            : '';
        const hiddenFlag = this.isPublicBusiness(business)
            ? ''
            : `<span class="hidden-flag" title="Hidden from public view">${this.escapeHtml(this.formatStatus(business.contactStatus || 'hidden'))}</span>`;
        if (this.hasValidEmail(business)) links.push(`<a href="mailto:${business.email}" class="card-link">✉️ Email</a>`);
        if (business.linkedin) links.push(`<a href="${business.linkedin}" target="_blank" class="card-link">💼 LinkedIn</a>`);
        if (business.instagram) links.push(`<a href="${business.instagram}" target="_blank" class="card-link">📷 Instagram</a>`);
        
        return `
            <article class="business-list-item ${isSelected ? 'selected' : ''}">
                <label class="select-checkbox">
                    <input type="checkbox" class="business-checkbox" data-id="${business.id}" ${isSelected}>
                    <span class="checkmark"></span>
                </label>
                <div class="list-item-main">
                    <div class="list-item-header">
                        <h3 class="card-title">${this.escapeHtml(business.company)}</h3>
                        <span class="card-category ${categoryClass}">${this.escapeHtml(business.category)}</span>
                        ${brandFlag}
                        ${hiddenFlag}
                        <span class="card-county">${this.escapeHtml(business.county || business.state || '')}</span>
                    </div>
                    <div class="card-links">${links.join('')}</div>
                </div>
                <div class="list-item-actions">
                    ${business.phone ? `<a href="tel:${business.phone}" class="card-link">📞 ${this.escapeHtml(business.phone)}</a>` : ''}
                </div>
            </article>
        `;
    }
    
    createLinkHTML(url, label, icon) {
        const icons = {
            globe: '🌐',
            mail: '✉️',
            linkedin: '💼',
            instagram: '📷',
            facebook: '👤'
        };
        return `<a href="${url}" target="_blank" class="card-link">${icons[icon]} ${label}</a>`;
    }

    hasValidEmail(business) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(business.email || '').trim());
    }

    isPublicBusiness(business) {
        return business.publicationStatus !== 'hidden' && this.hasValidEmail(business);
    }

    formatStatus(status) {
        return String(status || '')
            .replace(/_/g, ' ')
            .replace(/\b\w/g, char => char.toUpperCase());
    }
    
    getCategoryClass(category) {
        const map = {
            'Engraver': 'category-engraving',
            'Distributor': 'category-signage',
            'Sign Company': 'category-trophies'
        };
        return map[category] || '';
    }
    
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new BusinessDirectory();
});
