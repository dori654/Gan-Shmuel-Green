// Configuration
const API_BASE_URL = 'http://localhost:5000'; // Adjust this to match your Flask backend URL

// Global state
let trucks = [];
let sessions = [];
let unknownTrucks = [];
let registeredContainers = [];
let historyItems = { trucks: [], containers: [] };

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);
});

// Initialize application
async function initializeApp() {
    try {
        showLoading(true);
        await loadTrucks();
        await loadSessions();
        await loadUnknownTrucks();
        await loadRegisteredContainers();
        await loadHistoryItems();
        setupEventListeners();
        showToast('המערכת נטענה בהצלחה', 'success');
    } catch (error) {
        console.error('Error initializing app:', error);
        showToast('שגיאה בטעינת המערכת', 'error');
    } finally {
        showLoading(false);
    }
}

// Setup event listeners
function setupEventListeners() {
    // Weighing form
    document.getElementById('weighingForm').addEventListener('submit', handleWeighingSubmit);
    
    // Container form
    document.getElementById('containerForm').addEventListener('submit', handleContainerSubmit);
    
    // Session filter
    document.getElementById('sessionFilter').addEventListener('change', filterSessions);
    
    // Auto-update scale display when form fields change
    const truckEntry = document.getElementById('truckEntry');
    const truckExit = document.getElementById('truckExit');
    const containerSelect = document.getElementById('containers');
    const brutoInput = document.getElementById('bruto');
    const directionSelect = document.getElementById('direction');
    
    if (truckEntry) {
        truckEntry.addEventListener('change', handleTruckChange);
    }
    if (truckExit) {
        truckExit.addEventListener('change', handleTruckChange);
    }
    if (containerSelect) {
        containerSelect.addEventListener('change', updateScaleDisplay);
    }
    if (brutoInput) {
        brutoInput.addEventListener('input', updateScaleDisplay);
    }
    if (directionSelect) {
        directionSelect.addEventListener('change', handleDirectionChange);
    }
}

// Auto-update scale display
async function updateScaleDisplay() {
    await getCurrentWeight();
}

// Handle direction change to filter truck options
// Handle truck selection change
async function handleTruckChange() {
    const direction = document.getElementById('direction').value;
    
    // Get truck value from appropriate field based on direction
    let selectedTruck;
    if (direction === 'out') {
        selectedTruck = document.getElementById('truckExit').value;
    } else {
        selectedTruck = document.getElementById('truckEntry').value;
    }
    
    if (direction === 'out' && selectedTruck) {
        // For exit weighing, populate containers with truck's entry containers
        await populateExitContainers(selectedTruck);
    } else if (direction === 'in') {
        // For entry weighing, populate all registered containers
        await loadRegisteredContainers();
    }
    
    // Update scale display
    updateScaleDisplay();
}

function handleDirectionChange() {
    const direction = document.getElementById('direction').value;
    const truckEntry = document.getElementById('truckEntry');
    const truckExit = document.getElementById('truckExit');
    const produceSelect = document.getElementById('produce');
    const brutoInput = document.getElementById('bruto');
    const containersSelect = document.getElementById('containers');
    const weightInputGroup = document.getElementById('bruto').closest('.form-group');
    const submitButton = document.querySelector('#weighingForm button[type="submit"]');
    
    // If no direction selected, disable all fields
    if (!direction) {
        [truckEntry, truckExit, produceSelect, brutoInput, containersSelect].forEach(field => {
            if (field) {
                field.disabled = true;
                field.style.display = 'none';
            }
        });
        return;
    }
    
    // Enable fields when direction is selected
    [produceSelect, containersSelect].forEach(field => {
        if (field) field.disabled = false;
    });
    
    if (direction === 'out') {
        // For exit: hide entry dropdown, show exit dropdown
        truckEntry.style.display = 'none';
        truckEntry.removeAttribute('required');
        truckEntry.disabled = true;
        truckEntry.removeAttribute('name');
        
        truckExit.style.display = 'block';
        truckExit.setAttribute('required', 'required');
        truckExit.setAttribute('name', 'truck'); // Use truck name for form submission
        truckExit.disabled = false;
        
        // Populate trucks for exit
        populateTrucksForExit();
        
        // Hide and disable weight input for exit weighing
        if (weightInputGroup) {
            weightInputGroup.style.display = 'none';
        }
        brutoInput.disabled = true;
        
        // Update produce dropdown
        if (produceSelect) {
            produceSelect.innerHTML = '<option value="">בחר תוצרת...</option><option value="oranges">תפוזים</option><option value="lemons">לימונים</option><option value="grapefruits">אשכוליות</option><option value="apples">תפוחים</option><option value="other">אחר</option>';
        }
        
        // Change submit button text for exit
        if (submitButton) {
            submitButton.innerHTML = '<i class="fas fa-truck"></i> שמור יציאת משאית';
        }
        
        showToast('מציג רק משאיות שנכנסו ולא יצאו - משקל יותמד אוטומטית', 'info');
    } else {
        // For entry: show entry dropdown, hide exit dropdown
        truckEntry.style.display = 'block';
        truckEntry.setAttribute('required', 'required');
        truckEntry.setAttribute('name', 'truck'); // Use truck name for form submission
        truckEntry.disabled = false;
        
        truckExit.style.display = 'none';
        truckExit.removeAttribute('required');
        truckExit.removeAttribute('name');
        truckExit.disabled = true;
        
        // Show and enable weight input for entry weighing
        if (weightInputGroup) {
            weightInputGroup.style.display = 'block';
        }
        brutoInput.disabled = false;
        brutoInput.placeholder = 'הכנס משקל התוצרת בלבד';
        
        // Update produce dropdown
        if (produceSelect) {
            produceSelect.innerHTML = '<option value="">בחר תוצרת...</option><option value="oranges">תפוזים</option><option value="lemons">לימונים</option><option value="grapefruits">אשכוליות</option><option value="apples">תפוחים</option><option value="other">אחר</option>';
        }
        
        // Load registered containers for entry
        loadRegisteredContainers();
        
        // Change submit button text for entry
        if (submitButton) {
            submitButton.innerHTML = '<i class="fas fa-save"></i> שמור שקילה';
        }
        
        if (direction === 'in') {
            showToast('הכנס מספר משאית בפורמט T-XXXXX', 'info');
        }
    }
    
    // Clear current values and update scale
    truckInput.value = '';
    truckSelect.value = '';
    document.getElementById('bruto').value = '';
    updateScaleDisplay();
}

// Global current time variable - updated every second
let globalCurrentTime = new Date();

// Update current time display and global time variable
function updateCurrentTime() {
    globalCurrentTime = new Date();
    const timeString = globalCurrentTime.toLocaleString('he-IL', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
    document.getElementById('currentTime').textContent = timeString;
}

// Get current time from the header clock (centralized time source)
function getCurrentTime() {
    return globalCurrentTime;
}

// Format datetime for display (uses centralized time)
function formatCurrentDateTime() {
    return globalCurrentTime.toLocaleString('he-IL', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// Tab management
function showTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all nav tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName + '-tab').classList.add('active');
    
    // Add active class to clicked nav tab
    event.target.classList.add('active');
    
    // Load data for specific tabs
    if (tabName === 'sessions') {
        loadSessions();
    } else if (tabName === 'unknown') {
        loadUnknownTrucks();
    }
}

// Load trucks from backend
async function loadTrucks() {
    try {
        // Fetch trucks from the JSON file via backend
        const response = await fetch(`${API_BASE_URL}/trucks`);
        if (response.ok) {
            const trucksData = await response.json();
            trucks = trucksData;
            
            // Populate the truck entry dropdown
            const truckEntry = document.getElementById('truckEntry');
            if (truckEntry) {
                truckEntry.innerHTML = '<option value="">בחר משאית לכניסה...</option>';
                
                trucksData.forEach(truck => {
                    const option = document.createElement('option');
                    option.value = truck.id;
                    option.textContent = `${truck.id} (${truck.weight} ${truck.unit})`;
                    truckEntry.appendChild(option);
                });
            }
        } else {
            // Fallback to hardcoded truck list if API fails
            const fallbackTrucks = [
                {id: 'T-14409', weight: 528, unit: 'lbs'},
                {id: 'T-16474', weight: 682, unit: 'lbs'},
                {id: 'T-14964', weight: 543, unit: 'lbs'},
                {id: 'T-17194', weight: 543, unit: 'lbs'},
                {id: 'T-17250', weight: 563, unit: 'lbs'},
                {id: 'T-14045', weight: 563, unit: 'lbs'},
                {id: 'T-14263', weight: 561, unit: 'lbs'},
                {id: 'T-17164', weight: 631, unit: 'lbs'},
                {id: 'T-16810', weight: 653, unit: 'lbs'},
                {id: 'T-17077', weight: 550, unit: 'lbs'},
                {id: 'T-13972', weight: 629, unit: 'lbs'},
                {id: 'T-13982', weight: 583, unit: 'lbs'},
                {id: 'T-15689', weight: 675, unit: 'lbs'},
                {id: 'T-14664', weight: 541, unit: 'lbs'},
                {id: 'T-14623', weight: 609, unit: 'lbs'},
                {id: 'T-14873', weight: 528, unit: 'lbs'},
                {id: 'T-14064', weight: 539, unit: 'lbs'},
                {id: 'T-13799', weight: 532, unit: 'lbs'},
                {id: 'T-15861', weight: 629, unit: 'lbs'},
                {id: 'T-16584', weight: 633, unit: 'lbs'},
                {id: 'T-17267', weight: 539, unit: 'lbs'},
                {id: 'T-16617', weight: 567, unit: 'lbs'},
                {id: 'T-16270', weight: 587, unit: 'lbs'},
                {id: 'T-14969', weight: 666, unit: 'lbs'},
                {id: 'T-15521', weight: 558, unit: 'lbs'},
                {id: 'T-16556', weight: 558, unit: 'lbs'},
                {id: 'T-17744', weight: 536, unit: 'lbs'},
                {id: 'T-17412', weight: 646, unit: 'lbs'},
                {id: 'T-15733', weight: 651, unit: 'lbs'},
                {id: 'T-14091', weight: 534, unit: 'lbs'},
                {id: 'T-14129', weight: 611, unit: 'lbs'}
            ];
            
            trucks = fallbackTrucks;
            
            const truckEntry = document.getElementById('truckEntry');
            if (truckEntry) {
                truckEntry.innerHTML = '<option value="">בחר משאית לכניסה...</option>';
                
                fallbackTrucks.forEach(truck => {
                    const option = document.createElement('option');
                    option.value = truck.id;
                    option.textContent = `${truck.id} (${truck.weight} ${truck.unit})`;
                    truckEntry.appendChild(option);
                });
            }
        }
        
        // Populate history dropdown if containers are already loaded
        if (registeredContainers.length > 0) {
            populateHistoryDropdown();
        }
    } catch (error) {
        console.error('Error loading trucks:', error);
        showToast('שגיאה בטעינת רשימת המשאיות', 'error');
    }
}

// Populate all trucks (for entry direction)
function populateAllTrucks() {
    const truckSelect = document.getElementById('truck');
    truckSelect.innerHTML = '<option value="">בחר משאית...</option>';
    
    const mockTruckIds = [
        'T-14409', 'T-16474', 'T-14964', 'T-17194', 'T-17250', 'T-14045',
        'T-14263', 'T-17164', 'T-16810', 'T-17077', 'T-13972', 'T-13982',
        'T-15689', 'T-14664', 'T-14623', 'T-14873', 'T-14064', 'T-13799',
        'T-15861', 'T-16584', 'T-17267', 'T-16617', 'T-16270', 'T-14969',
        'T-15521', 'T-16556', 'T-17744', 'T-17412', 'T-15733', 'T-14091', 'T-14129'
    ];
    
    mockTruckIds.forEach(truck => {
        const option = document.createElement('option');
        option.value = truck;
        option.textContent = truck;
        truckSelect.appendChild(option);
    });
}

// Get containers that a truck entered with
async function getTruckEntryContainers(truckId) {
    try {
        const response = await fetch(`${API_BASE_URL}/weight`);
        if (response.ok) {
            const allTransactions = await response.json();
            
            // Find the most recent 'in' transaction for this truck
            const truckInTransaction = allTransactions
                .filter(t => t.truck === truckId && t.direction === 'in')
                .sort((a, b) => new Date(b.datetime) - new Date(a.datetime))[0];
            
            if (truckInTransaction && truckInTransaction.containers) {
                // Handle containers field (could be array or comma-separated string)
                let containers;
                if (Array.isArray(truckInTransaction.containers)) {
                    containers = truckInTransaction.containers;
                } else {
                    // Parse as comma-separated string
                    containers = truckInTransaction.containers
                        .split(',')
                        .map(c => c.trim())
                        .filter(c => c.length > 0);
                }
                return containers;
            }
        }
    } catch (error) {
        console.error('Error fetching truck entry containers:', error);
    }
    return [];
}

// Populate container dropdown for exit weighing with truck's entry containers
async function populateExitContainers(truckId) {
    const containerSelect = document.getElementById('containers');
    containerSelect.innerHTML = '<option value="">בחר מכולה...</option>';
    
    if (!truckId) return;
    
    const entryContainers = await getTruckEntryContainers(truckId);
    
    if (entryContainers.length > 0) {
        entryContainers.forEach(containerId => {
            const option = document.createElement('option');
            option.value = containerId;
            option.textContent = containerId;
            containerSelect.appendChild(option);
        });
        
        showToast(`נמצאו ${entryContainers.length} מכולות שנכנסו עם המשאית`, 'info');
    } else {
        const option = document.createElement('option');
        option.value = '';
        option.disabled = true;
        option.textContent = 'לא נמצאו מכולות';
        containerSelect.appendChild(option);
        
        showToast('לא נמצאו מכולות שנכנסו עם המשאית', 'warning');
    }
}

// Populate trucks for exit (only trucks that entered but didn't exit)
async function populateTrucksForExit() {
    const truckExit = document.getElementById('truckExit');
    truckExit.innerHTML = '<option value="">בחר משאית ליציאה...</option>';
    
    try {
        // Get all transactions from the weight endpoint
        const response = await fetch(`${API_BASE_URL}/weight`);
        if (response.ok) {
            const allTransactions = await response.json();
            
            // Cache transactions globally for truck tara lookup
            window.allTransactions = allTransactions;
            
            // Find trucks that have 'in' direction but no corresponding 'out'
            const trucksIn = new Map();
            const trucksOut = new Set();
            
            // First pass: collect all 'in' transactions and 'out' truck IDs
            allTransactions.forEach(transaction => {
                if (transaction.direction === 'in' && transaction.truck) {
                    // Store the latest 'in' transaction for each truck
                    if (!trucksIn.has(transaction.truck) || 
                        new Date(transaction.datetime) > new Date(trucksIn.get(transaction.truck).datetime)) {
                        trucksIn.set(transaction.truck, transaction);
                    }
                } else if (transaction.direction === 'out' && transaction.truck) {
                    trucksOut.add(transaction.truck);
                }
            });
            
            // Find trucks that entered but haven't exited
            const trucksForExit = [];
            trucksIn.forEach((inTransaction, truckId) => {
                if (!trucksOut.has(truckId)) {
                    trucksForExit.push(inTransaction);
                }
            });
            
            // Sort by datetime (most recent first)
            trucksForExit.sort((a, b) => new Date(b.datetime) - new Date(a.datetime));
            
            if (trucksForExit.length > 0) {
                trucksForExit.forEach(truck => {
                    const option = document.createElement('option');
                    option.value = truck.truck;
                    option.textContent = `${truck.truck} (נכנס ב-${formatDateTime(truck.datetime)})`;
                    truckExit.appendChild(option);
                });
                
                showToast(`נמצאו ${trucksForExit.length} משאיות ליציאה`, 'success');
            } else {
                const option = document.createElement('option');
                option.value = '';
                option.disabled = true;
                option.textContent = 'אין משאיות ליציאה';
                truckExit.appendChild(option);
                
                showToast('כל המשאיות יצאו! 🎉', 'success');
            }
        } else {
            throw new Error('Failed to fetch transactions');
        }
    } catch (error) {
        console.error('Error loading trucks for exit:', error);
        // Fallback to mock data
        const mockUnknownTrucks = ['T-14263', 'T-16474', 'T-17194'];
        
        mockUnknownTrucks.forEach(truck => {
            const option = document.createElement('option');
            option.value = truck;
            option.textContent = `${truck} (משאית ליציאה)`;
            truckExit.appendChild(option);
        });
        
        showToast('שגיאה בטעינת נתונים - מציג נתוני דמו', 'warning');
    }
}

// Load sessions from backend
async function loadSessions() {
    try {
        const response = await fetch(`${API_BASE_URL}/weight`);
        if (!response.ok) {
            throw new Error('Failed to fetch sessions');
        }
        
        sessions = await response.json();
        
        // Cache transactions globally for truck tara lookup
        window.allTransactions = sessions;
        
        displaySessions(sessions);
    } catch (error) {
        console.error('Error loading sessions:', error);
        showToast('שגיאה בטעינת רשימת הפעולות', 'error');
        // Show mock data for demo
        displayMockSessions();
    }
}

// Display sessions in table
function displaySessions(sessionsData) {
    const tbody = document.getElementById('sessionsTableBody');
    tbody.innerHTML = '';
    
    if (!sessionsData || sessionsData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" style="text-align: center;">אין נתונים להצגה</td></tr>';
        return;
    }
    
    sessionsData.forEach(session => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${session.id || '-'}</td>
            <td>${formatDateTime(session.datetime)}</td>
            <td>${session.truck || '-'}</td>
            <td><span class="status-badge status-${session.direction}">${session.direction === 'in' ? 'כניסה' : 'יציאה'}</span></td>
            <td>${session.produce || '-'}</td>
            <td>${session.bruto ? session.bruto + ' ק"ג' : '-'}</td>
            <td>${session.truckTara ? session.truckTara + ' ק"ג' : '-'}</td>
            <td>${session.neto ? session.neto + ' ק"ג' : '-'}</td>
            <td>${session.containers || '-'}</td>
            <td>
                <button class="btn btn-info" onclick="viewSession(${session.id})" title="צפה בפרטים">
                    <i class="fas fa-eye"></i>
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Display mock sessions for demo
function displayMockSessions() {
    const mockSessions = [
        {
            id: 1,
            datetime: getCurrentTime().toISOString(),
            truck: 'T-14263',
            direction: 'in',
            produce: 'תפוזים',
            bruto: 1500,
            truckTara: null,
            neto: null,
            containers: 'C-001, C-002'
        },
        {
            id: 2,
            datetime: new Date(Date.now() - 3600000).toISOString(),
            truck: 'T-16474',
            direction: 'out',
            produce: 'לימונים',
            bruto: 800,
            truckTara: 682,
            neto: 118,
            containers: 'C-003'
        }
    ];
    
    displaySessions(mockSessions);
}

// Load unknown trucks
async function loadUnknownTrucks() {
    try {
        // Get all transactions
        const response = await fetch(`${API_BASE_URL}/weight`);
        if (!response.ok) {
            throw new Error('Failed to fetch transactions');
        }
        
        const transactions = await response.json();
        
        // Find trucks that entered but haven't exited
        const trucksIn = transactions.filter(t => t.direction === 'in');
        const trucksOut = transactions.filter(t => t.direction === 'out');
        
        const trucksNotClosed = trucksIn.filter(inTruck => {
            // Check if this truck has a corresponding exit transaction
            const hasExit = trucksOut.some(outTruck => 
                outTruck.truck === inTruck.truck && 
                new Date(outTruck.datetime) > new Date(inTruck.datetime)
            );
            return !hasExit;
        });
        
        unknownTrucks = trucksNotClosed;
        displayUnknownTrucks(unknownTrucks);
    } catch (error) {
        console.error('Error loading trucks not closed:', error);
        showToast('שגיאה בטעינת רשימת המשאיות הלא סגורות', 'error');
        // Show empty list on error
        displayUnknownTrucks([]);
    }
}

// Display unknown trucks
function displayUnknownTrucks(trucksData) {
    const container = document.getElementById('unknownTrucksList');
    container.innerHTML = '';
    
    if (!trucksData || trucksData.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #27ae60; font-weight: 600;">כל המשאיות סגורות! 🎉</p>';
        return;
    }
    
    trucksData.forEach(truck => {
        const card = document.createElement('div');
        card.className = 'unknown-truck-card';
        card.innerHTML = `
            <h4><i class="fas fa-truck"></i> ${truck.truck}</h4>
            <p><i class="fas fa-calendar"></i> תאריך כניסה: ${formatDateTime(truck.datetime)}</p>
            <p><i class="fas fa-leaf"></i> תוצרת: ${truck.produce}</p>
            <p><i class="fas fa-weight"></i> משקל ברוטו: ${truck.bruto} ק"ג</p>
            <p><i class="fas fa-box"></i> מכולות: ${Array.isArray(truck.containers) ? truck.containers.join(', ') : (truck.containers || 'ללא')}</p>
            <button class="btn btn-warning" onclick="createOutWeighing('${truck.truck}', '${truck.produce}')" style="margin-top: 1rem;">
                <i class="fas fa-sign-out-alt"></i> צור שקילת יציאה
            </button>
        `;
        container.appendChild(card);
    });
}

// Display mock unknown trucks for demo
function displayMockUnknownTrucks() {
    const mockUnknown = [
        {
            truck: 'T-14263',
            datetime: getCurrentTime().toISOString(),
            produce: 'תפוזים',
            bruto: 1500,
            containers: 'C-001, C-002'
        }
    ];
    
    displayUnknownTrucks(mockUnknown);
}

// Load registered containers
async function loadRegisteredContainers() {
    try {
        const response = await fetch(`${API_BASE_URL}/containers`);
        if (!response.ok) {
            throw new Error('Failed to fetch registered containers');
        }
        
        const data = await response.json();
        registeredContainers = data.containers || [];
        populateContainersDropdown(registeredContainers);
        populateHistoryDropdown();
    } catch (error) {
        console.error('Error loading registered containers:', error);
        showToast('שגיאה בטעינת רשימת המכולות', 'error');
        // Show mock data for demo
        populateMockContainers();
    }
}

// Load history items (trucks and containers from actual transactions)
async function loadHistoryItems() {
    try {
        const response = await fetch(`${API_BASE_URL}/history-items`);
        if (!response.ok) {
            throw new Error('Failed to fetch history items');
        }
        
        historyItems = await response.json();
        populateHistoryDropdownFromHistory();
    } catch (error) {
        console.error('Error loading history items:', error);
        showToast('שגיאה בטעינת רשימת ההיסטוריה', 'error');
        // Fallback to mock data
        populateMockHistoryItems();
    }
}

// Populate containers dropdown
function populateContainersDropdown(containers) {
    const select = document.getElementById('containers');
    select.innerHTML = '<option value="">בחר מכולה...</option>';
    
    if (!containers || containers.length === 0) {
        const option = document.createElement('option');
        option.value = '';
        option.disabled = true;
        option.textContent = 'אין מכולות רשומות';
        select.appendChild(option);
        return;
    }
    
    containers.forEach(container => {
        const option = document.createElement('option');
        option.value = container.container_id;
        option.textContent = `${container.container_id} (${container.weight} ${container.unit})`;
        select.appendChild(option);
    });
}

// Populate mock containers for demo (fallback)
function populateMockContainers() {
    const mockContainers = [
        { container_id: 'C-001', weight: 100, unit: 'kg' },
        { container_id: 'C-002', weight: 150, unit: 'kg' },
        { container_id: 'C-003', weight: 120, unit: 'kg' },
        { container_id: 'C-004', weight: 180, unit: 'kg' },
        { container_id: 'C-005', weight: 90, unit: 'kg' }
    ];
    
    populateContainersDropdown(mockContainers);
    showToast('מציג מכולות דמו - בעיה בטעינת API', 'warning');
}

// Populate history search dropdown with trucks and containers
function populateHistoryDropdown() {
    const select = document.getElementById('itemId');
    select.innerHTML = '<option value="">בחר פריט...</option>';
    
    // Add trucks section
    if (trucks && trucks.length > 0) {
        const trucksGroup = document.createElement('optgroup');
        trucksGroup.label = 'משאיות';
        
        trucks.forEach(truck => {
            const option = document.createElement('option');
            option.value = truck.id;
            option.textContent = `${truck.id} (משאית)`;
            trucksGroup.appendChild(option);
        });
        
        select.appendChild(trucksGroup);
    }
    
    // Add containers section
    if (registeredContainers && registeredContainers.length > 0) {
        const containersGroup = document.createElement('optgroup');
        containersGroup.label = 'מכולות';
        
        registeredContainers.forEach(container => {
            const option = document.createElement('option');
            option.value = container.container_id;
            option.textContent = `${container.container_id} (מכולה - ${container.weight} ${container.unit})`;
            containersGroup.appendChild(option);
        });
        
        select.appendChild(containersGroup);
    }
    
    // If no data, add mock items
    if ((!trucks || trucks.length === 0) && (!registeredContainers || registeredContainers.length === 0)) {
        populateMockHistoryItems();
    }
}

// Populate history dropdown from actual transaction history
function populateHistoryDropdownFromHistory() {
    const select = document.getElementById('itemId');
    select.innerHTML = '<option value="">בחר פריט...</option>';
    
    // Add trucks section from actual history
    if (historyItems.trucks && historyItems.trucks.length > 0) {
        const trucksGroup = document.createElement('optgroup');
        trucksGroup.label = 'משאיות מההיסטוריה';
        
        historyItems.trucks.forEach(truck => {
            const option = document.createElement('option');
            option.value = truck;
            option.textContent = `${truck} (משאית)`;
            trucksGroup.appendChild(option);
        });
        
        select.appendChild(trucksGroup);
    }
    
    // Add containers section from actual history
    if (historyItems.containers && historyItems.containers.length > 0) {
        const containersGroup = document.createElement('optgroup');
        containersGroup.label = 'מכולות מההיסטוריה';
        
        historyItems.containers.forEach(container => {
            const option = document.createElement('option');
            option.value = container;
            option.textContent = `${container} (מכולה)`;
            containersGroup.appendChild(option);
        });
        
        select.appendChild(containersGroup);
    }
    
    // If no history data, fall back to mock items
    if ((!historyItems.trucks || historyItems.trucks.length === 0) && 
        (!historyItems.containers || historyItems.containers.length === 0)) {
        populateMockHistoryItems();
    }
}

// Populate mock history items for demo
function populateMockHistoryItems() {
    const select = document.getElementById('itemId');
    
    // Mock trucks
    const trucksGroup = document.createElement('optgroup');
    trucksGroup.label = 'משאיות';
    
    const mockTrucks = ['T-14263', 'T-15847', 'T-16932', 'T-17845', 'T-18756'];
    mockTrucks.forEach(truckId => {
        const option = document.createElement('option');
        option.value = truckId;
        option.textContent = `${truckId} (משאית)`;
        trucksGroup.appendChild(option);
    });
    
    select.appendChild(trucksGroup);
    
    // Mock containers
    const containersGroup = document.createElement('optgroup');
    containersGroup.label = 'מכולות';
    
    const mockContainers = [
        { container_id: 'C-001', weight: 100, unit: 'kg' },
        { container_id: 'C-002', weight: 150, unit: 'kg' },
        { container_id: 'C-003', weight: 120, unit: 'kg' },
        { container_id: 'C-004', weight: 180, unit: 'kg' },
        { container_id: 'C-005', weight: 90, unit: 'kg' }
    ];
    
    mockContainers.forEach(container => {
        const option = document.createElement('option');
        option.value = container.container_id;
        option.textContent = `${container.container_id} (מכולה - ${container.weight} ${container.unit})`;
        containersGroup.appendChild(option);
    });
    
    select.appendChild(containersGroup);
}

// Handle weighing form submission
async function handleWeighingSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    
    // Get selected container from dropdown
    const selectedContainer = formData.get('containers');
    const containers = selectedContainer ? [selectedContainer] : [];
    
    // Calculate the total bruto weight to send to API
    const direction = formData.get('direction');
    const selectedTruck = formData.get('truck');
    let totalBrutoWeight;
    
    if (direction === 'out') {
        // For exit weighing, use the weight from scale display
        totalBrutoWeight = parseFloat(document.getElementById('currentWeight').textContent) || 0;
    } else {
        // For entry weighing, calculate from produce input + tara weights
        const produceWeight = parseFloat(formData.get('bruto')) || 0;
        totalBrutoWeight = produceWeight;
        
        // Add truck tara
        if (selectedTruck) {
            const truckTara = getTruckTara(selectedTruck);
            totalBrutoWeight += truckTara;
        }
        
        // Add container weight
        if (selectedContainer) {
            const containerWeight = getContainerWeight(selectedContainer);
            totalBrutoWeight += containerWeight;
        }
    }
    
    const data = {
        truck: formData.get('truck'),
        direction: formData.get('direction'),
        produce: formData.get('produce'),
        weight: totalBrutoWeight, // Send calculated bruto weight
        containers: containers
    };
    
    try {
        showLoading(true);
        
        const response = await fetch(`${API_BASE_URL}/weight`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'שגיאה בשמירת השקילה');
        }
        
        const result = await response.json();
        
        // Show different success message based on direction
        if (direction === 'out') {
            showToast('יציאת המשאית נשמרה בהצלחה', 'success');
            // Show popup with tara and neto details for exit weighing
            showExitWeighingPopup(result, selectedTruck);
        } else {
            showToast('השקילה נשמרה בהצלחה', 'success');
        }
        
        // Reset form and refresh data
        event.target.reset();
        await loadSessions();
        await loadUnknownTrucks();
        
        // Show result details
        if (result.neto) {
            showToast(`משקל נטו: ${result.neto} ק"ג`, 'info');
        }
        
    } catch (error) {
        console.error('Error submitting weighing:', error);
        showToast(error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Handle container form submission
async function handleContainerSubmit(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const containerData = [{
        container_id: formData.get('containerId'),
        weight: parseFloat(formData.get('containerWeight')),
        unit: formData.get('containerUnit')
    }];
    
    try {
        showLoading(true);
        
        const response = await fetch(`${API_BASE_URL}/batch-weight`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(containerData)
        });
        
        if (!response.ok) {
            throw new Error('שגיאה ברישום המכולה');
        }
        
        showToast('המכולה נרשמה בהצלחה', 'success');
        event.target.reset();
        
    } catch (error) {
        console.error('Error registering container:', error);
        showToast(error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Upload containers from CSV
async function uploadContainers() {
    const fileInput = document.getElementById('csvFile');
    const file = fileInput.files[0];
    
    if (!file) {
        showToast('אנא בחר קובץ CSV', 'warning');
        return;
    }
    
    try {
        showLoading(true);
        
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE_URL}/batch-weight`, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('שגיאה בהעלאת הקובץ');
        }
        
        showToast('הקובץ הועלה בהצלחה', 'success');
        fileInput.value = '';
        
    } catch (error) {
        console.error('Error uploading file:', error);
        showToast(error.message, 'error');
    } finally {
        showLoading(false);
    }
}

// Search history
async function searchHistory() {
    const itemId = document.getElementById('itemId').value;
    const fromDate = document.getElementById('fromDate').value;
    const toDate = document.getElementById('toDate').value;
    
    if (!itemId) {
        showToast('אנא הכנס מזהה פריט', 'warning');
        return;
    }
    
    try {
        showLoading(true);
        
        let url = `${API_BASE_URL}/item/${itemId}`;
        const params = new URLSearchParams();
        
        if (fromDate) params.append('from', new Date(fromDate).getTime());
        if (toDate) params.append('to', new Date(toDate).getTime());
        
        if (params.toString()) {
            url += '?' + params.toString();
        }
        
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error('שגיאה בחיפוש ההיסטוריה');
        }
        
        const itemData = await response.json();
        
        // Get detailed session data for each session ID
        const sessionDetails = [];
        if (itemData.sessions && itemData.sessions.length > 0) {
            for (const sessionId of itemData.sessions) {
                try {
                    const sessionResponse = await fetch(`${API_BASE_URL}/session/${sessionId}`);
                    if (sessionResponse.ok) {
                        const sessionData = await sessionResponse.json();
                        sessionDetails.push({
                            id: sessionId,
                            truck: sessionData.truck,
                            bruto: sessionData.bruto,
                            truckTara: sessionData.truckTara,
                            neto: sessionData.neto,
                            itemId: itemId,
                            tara: itemData.tara
                        });
                    }
                } catch (sessionError) {
                    console.error(`Error fetching session ${sessionId}:`, sessionError);
                }
            }
        }
        
        displayHistoryResults(sessionDetails);
        
    } catch (error) {
        console.error('Error searching history:', error);
        showToast(error.message, 'error');
        // Show mock data for demo
        displayMockHistory(itemId);
    } finally {
        showLoading(false);
    }
}

// Display history results
function displayHistoryResults(historyData) {
    const container = document.getElementById('historyResults');
    container.innerHTML = '';
    
    if (!historyData || historyData.length === 0) {
        container.innerHTML = '<p style="text-align: center;">לא נמצאו תוצאות</p>';
        return;
    }
    
    historyData.forEach(item => {
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        historyItem.innerHTML = `
            <h4><i class="fas fa-history"></i> פעולה מספר ${item.id}</h4>
            <div class="details">
                <div class="detail">
                    <span class="detail-label">פריט מזהה</span>
                    <span class="detail-value">${item.itemId}</span>
                </div>
                <div class="detail">
                    <span class="detail-label">משאית</span>
                    <span class="detail-value">${item.truck || '-'}</span>
                </div>
                <div class="detail">
                    <span class="detail-label">משקל ברוטו</span>
                    <span class="detail-value">${item.bruto || '-'} ק"ג</span>
                </div>
                <div class="detail">
                    <span class="detail-label">משקל טרה</span>
                    <span class="detail-value">${item.truckTara || item.tara || '-'} ק"ג</span>
                </div>
                <div class="detail">
                    <span class="detail-label">משקל נטו</span>
                    <span class="detail-value"><strong>${item.neto !== undefined && item.neto !== 'na' ? item.neto + ' ק"ג' : 'לא זמין'}</strong></span>
                </div>
                <div class="detail">
                    <span class="detail-label">סטטוס</span>
                    <span class="detail-value">${item.neto !== undefined && item.neto !== 'na' ? 'פעולה שלמה' : 'ממתין ליציאה'}</span>
                </div>
            </div>
        `;
        container.appendChild(historyItem);
    });
}

// Display mock history for demo
function displayMockHistory(itemId) {
    const mockHistory = [
        {
            id: 1,
            datetime: getCurrentTime().toISOString(),
            direction: 'in',
            produce: 'תפוזים',
            bruto: 1500,
            neto: null,
            containers: 'C-001, C-002'
        }
    ];
    
    displayHistoryResults(mockHistory);
}

// Filter sessions
function filterSessions() {
    const filter = document.getElementById('sessionFilter').value;
    let filteredSessions = sessions;
    
    if (filter !== 'all') {
        if (filter === 'completed') {
            filteredSessions = sessions.filter(s => s.neto !== null);
        } else {
            filteredSessions = sessions.filter(s => s.direction === filter);
        }
    }
    
    displaySessions(filteredSessions);
}

// View session details
async function viewSession(sessionId) {
    try {
        const response = await fetch(`${API_BASE_URL}/session/${sessionId}`);
        if (!response.ok) {
            throw new Error('שגיאה בטעינת פרטי הפעולה');
        }
        
        const sessionData = await response.json();
        
        // Create modal or detailed view
        alert(`פרטי פעולה ${sessionId}:\n\nמשאית: ${sessionData.truck}\nתוצרת: ${sessionData.produce}\nמשקל ברוטו: ${sessionData.bruto} ק"ג\nמשקל נטו: ${sessionData.neto || 'לא זמין'} ק"ג`);
        
    } catch (error) {
        console.error('Error viewing session:', error);
        showToast(error.message, 'error');
    }
}

// Create out weighing for unknown truck
function createOutWeighing(truckId, produce) {
    // Pre-fill the weighing form
    document.getElementById('direction').value = 'out';
    document.getElementById('produce').value = produce;
    
    // Trigger direction change to show correct truck dropdown
    handleDirectionChange();
    
    // Set truck value in exit dropdown
    setTimeout(() => {
        document.getElementById('truckExit').value = truckId;
    }, 100);
    
    // Switch to weighing tab
    showTab('weighing');
    
    // Focus on weight input
    document.getElementById('bruto').focus();
    
    showToast(`טופס שקילת יציאה הוכן עבור משאית ${truckId}`, 'info');
}

// Get current weight from scale - calculates according to: Bruto = Neto (fruit) + Tara (truck) + sum(Tara (containers))
async function getCurrentWeight() {
    const direction = document.getElementById('direction').value;
    const selectedContainer = document.getElementById('containers').value;
    
    // Get truck value from appropriate field based on direction
    let selectedTruck;
    if (direction === 'out') {
        selectedTruck = document.getElementById('truckExit').value;
    } else {
        selectedTruck = document.getElementById('truckEntry').value;
    }
    
    if (direction === 'out') {
        // For exit weighing: get the bruto weight from the entry session
        let entryBrutoWeight = 0;
        if (selectedTruck) {
            entryBrutoWeight = await getEntryBrutoWeight(selectedTruck);
        }
        
        // Update scale display with entry bruto weight
        document.getElementById('currentWeight').textContent = entryBrutoWeight.toFixed(1);
        
        if (selectedTruck) {
            // Get truck tara for calculation display
            const truckTara = getTruckTara(selectedTruck);
            
            // Get container weight if selected
            let containerWeight = 0;
            if (selectedContainer) {
                containerWeight = getContainerWeight(selectedContainer);
            }
            
            // Calculate neto: Neto = Bruto - Truck Tara - Container Weight
            const calculatedNeto = entryBrutoWeight - truckTara - containerWeight;
            
            let breakdown = [];
            breakdown.push(`ברוטו (מכניסה): ${entryBrutoWeight} ק"ג`);
            if (truckTara > 0) {
                breakdown.push(`טרה משאית: ${truckTara} ק"ג`);
            }
            if (containerWeight > 0) {
                breakdown.push(`טרה מכולה: ${containerWeight} ק"ג`);
            }
            breakdown.push(`נטו (מחושב): ${calculatedNeto.toFixed(1)} ק"ג`);
            
            const breakdownText = breakdown.join('<br>');
            showToast(`יציאה:<br>${breakdownText}`, 'info');
        } else {
            showToast(`משקל מכניסה: ${entryBrutoWeight} ק"ג`, 'info');
        }
        
        return;
    }
    
    // For entry weighing: calculate bruto from produce input
    const produceWeight = parseFloat(document.getElementById('bruto').value) || 0;
    
    // Calculate bruto weight: Bruto = Neto (produce) + Tara (truck) + sum(Tara (containers))
    let calculatedBruto = 0;
    let weightBreakdown = [];
    
    // Add produce weight (neto) if entered
    if (produceWeight > 0) {
        calculatedBruto += produceWeight;
        weightBreakdown.push(`תוצרת (נטו): ${produceWeight} ק"ג`);
    }
    
    // Add truck tara if selected
    if (selectedTruck) {
        const truckTara = getTruckTara(selectedTruck);
        if (truckTara > 0) {
            calculatedBruto += truckTara;
            weightBreakdown.push(`משאית: ${truckTara} ק"ג`);
        }
    }
    
    // Add container weight if selected
    if (selectedContainer) {
        const containerWeight = getContainerWeight(selectedContainer);
        if (containerWeight > 0) {
            calculatedBruto += containerWeight;
            weightBreakdown.push(`מכולה: ${containerWeight} ק"ג`);
        }
    }
    
    // Update scale display with calculated bruto weight
    const displayWeight = calculatedBruto.toFixed(1);
    document.getElementById('currentWeight').textContent = displayWeight;
    
    // Show breakdown of calculation
    if (calculatedBruto > 0) {
        const breakdownText = weightBreakdown.join(' + ');
        if (weightBreakdown.length > 1) {
            showToast(`כניסה: ברוטו מחושב ${displayWeight} ק"ג<br>${breakdownText}`, 'info');
        } else {
            showToast(`משקל: ${displayWeight} ק"ג`, 'info');
        }
    } else {
        document.getElementById('currentWeight').textContent = '0.0';
        showToast('הכנס משקל ובחר משאית/מכולה', 'warning');
    }
}

// Helper function to get truck tara weight
function getTruckTara(truckId) {
    const direction = document.getElementById('direction').value;
    
    // For exit weighing, get truck tara from the entry transaction in database
    if (direction === 'out') {
        return getTruckTaraFromDatabase(truckId);
    }
    
    // For entry weighing, use truck data from loaded trucks array
    const truck = trucks.find(t => t.id === truckId);
    if (truck) {
        // Convert from lbs to kg if needed
        if (truck.unit === 'lbs') {
            return convertLbsToKg(truck.weight);
        } else {
            return truck.weight;
        }
    }
    
    return 0; // Default if truck not found
}

// Get truck tara from database transaction (for exit weighing)
function getTruckTaraFromDatabase(truckId) {
    // Check if we have cached transaction data
    if (window.allTransactions) {
        const truckInTransaction = window.allTransactions
            .filter(t => t.direction === 'in' && t.truck === truckId)
            .sort((a, b) => new Date(b.datetime) - new Date(a.datetime))[0];
        
        if (truckInTransaction && truckInTransaction.truckTara) {
            return truckInTransaction.truckTara;
        }
    }
    
    // Fallback to loaded truck data if no database tara found
    const truck = trucks.find(t => t.id === truckId);
    if (truck) {
        // Convert from lbs to kg if needed
        if (truck.unit === 'lbs') {
            return convertLbsToKg(truck.weight);
        } else {
            return truck.weight;
        }
    }
    
    return 1180; // Default weight if truck not found
}

// Helper function to convert pounds to kilograms
function convertLbsToKg(weightInLbs) {
    return Math.round(weightInLbs * 0.45359237);
}

// Get entry bruto weight from database transaction (for exit weighing)
async function getEntryBrutoWeight(truckId) {
    try {
        // First check if we have cached transaction data
        if (window.allTransactions) {
            const truckInTransaction = window.allTransactions
                .filter(t => t.direction === 'in' && t.truck === truckId)
                .sort((a, b) => new Date(b.datetime) - new Date(a.datetime))[0];
            
            if (truckInTransaction && truckInTransaction.weight) {
                return truckInTransaction.weight;
            }
        }
        
        // If not cached, fetch from API
        const response = await fetch(`${API_BASE_URL}/sessions`);
        if (!response.ok) {
            throw new Error('Failed to fetch sessions');
        }
        
        const sessions = await response.json();
        const truckInSession = sessions
            .filter(s => s.direction === 'in' && s.truck === truckId)
            .sort((a, b) => new Date(b.datetime) - new Date(a.datetime))[0];
        
        if (truckInSession && truckInSession.weight) {
            return truckInSession.weight;
        }
        
        return 0; // Default if no entry found
    } catch (error) {
        console.error('Error getting entry bruto weight:', error);
        return 0;
    }
}

// Helper function to get container weight
function getContainerWeight(containerId) {
    // Find container weight from registered containers
    const container = registeredContainers.find(c => c.container_id === containerId);
    if (container) {
        return parseFloat(container.weight) || 0;
    }
    
    // Fallback to mock weights if not found
    const mockWeights = {
        'C-001': 100, 'C-002': 150, 'C-003': 120,
        'C-004': 180, 'C-005': 90
    };
    
    return mockWeights[containerId] || 0;
}

// Refresh all data
async function refreshData() {
    try {
        showLoading(true);
        await loadSessions();
        await loadUnknownTrucks();
        showToast('הנתונים רוענו בהצלחה', 'success');
    } catch (error) {
        console.error('Error refreshing data:', error);
        showToast('שגיאה ברענון הנתונים', 'error');
    } finally {
        showLoading(false);
    }
}

// Utility functions
function formatDateTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleString('he-IL', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = show ? 'flex' : 'none';
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    }[type];
    
    toast.innerHTML = `
        <i class="${icon}"></i>
        <span>${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    container.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 5000);
}

// Show exit weighing popup with tara and neto details
function showExitWeighingPopup(result, truckId) {
    // Create popup overlay
    const overlay = document.createElement('div');
    overlay.className = 'popup-overlay';
    overlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 1000;
    `;
    
    // Create popup content
    const popup = document.createElement('div');
    popup.className = 'popup-content';
    popup.style.cssText = `
        background: white;
        border-radius: 10px;
        padding: 30px;
        max-width: 500px;
        width: 90%;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        text-align: center;
        direction: rtl;
    `;
    
    // Get container weight if available
    const selectedContainer = document.getElementById('containers').value;
    let containerWeight = 0;
    if (selectedContainer) {
        containerWeight = getContainerWeight(selectedContainer);
    }
    
    // Calculate bruto weight from scale display
    const brutoWeight = parseFloat(document.getElementById('currentWeight').textContent) || 0;
    
    // Create popup HTML
    popup.innerHTML = `
        <div style="margin-bottom: 20px;">
            <i class="fas fa-truck" style="font-size: 48px; color: #28a745; margin-bottom: 15px;"></i>
            <h2 style="color: #28a745; margin: 0 0 10px 0;">יציאת משאית הושלמה בהצלחה!</h2>
            <p style="color: #666; margin: 0;">משאית: ${truckId}</p>
        </div>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin: 0 0 15px 0; color: #333;">פירוט שקילה:</h3>
            
            <div style="display: flex; justify-content: space-between; margin: 10px 0; padding: 8px 0; border-bottom: 1px solid #dee2e6;">
                <span style="font-weight: bold;">משקל ברוטו (ממוזן):</span>
                <span style="color: #007bff; font-weight: bold;">${brutoWeight.toFixed(1)} ק"ג</span>
            </div>
            
            <div style="display: flex; justify-content: space-between; margin: 10px 0; padding: 8px 0; border-bottom: 1px solid #dee2e6;">
                <span style="font-weight: bold;">טרה משאית:</span>
                <span style="color: #dc3545; font-weight: bold;">${result.truckTara || 0} ק"ג</span>
            </div>
            
            ${containerWeight > 0 ? `
            <div style="display: flex; justify-content: space-between; margin: 10px 0; padding: 8px 0; border-bottom: 1px solid #dee2e6;">
                <span style="font-weight: bold;">טרה מכולה:</span>
                <span style="color: #dc3545; font-weight: bold;">${containerWeight} ק"ג</span>
            </div>
            ` : ''}
            
            <div style="display: flex; justify-content: space-between; margin: 15px 0 0 0; padding: 12px 0; border-top: 2px solid #28a745; font-size: 18px;">
                <span style="font-weight: bold; color: #28a745;">משקל נטו (תוצרת):</span>
                <span style="color: #28a745; font-weight: bold; font-size: 20px;">${result.neto || 'N/A'} ק"ג</span>
            </div>
        </div>
        
        <button onclick="this.closest('.popup-overlay').remove()" 
                style="background: #28a745; color: white; border: none; padding: 12px 30px; border-radius: 5px; font-size: 16px; cursor: pointer; margin-top: 10px;">
            <i class="fas fa-check"></i> אשר
        </button>
    `;
    
    overlay.appendChild(popup);
    document.body.appendChild(overlay);
    
    // Close popup when clicking outside
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.remove();
        }
    });
    
    // Close popup with Escape key
    const handleEscape = (e) => {
        if (e.key === 'Escape') {
            overlay.remove();
            document.removeEventListener('keydown', handleEscape);
        }
    };
    document.addEventListener('keydown', handleEscape);
}

// Real weight calculation is now handled by getCurrentWeight() function
// Called automatically when form inputs change
