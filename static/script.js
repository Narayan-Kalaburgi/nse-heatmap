function updateClock() {
    const clockEl = document.getElementById('live-clock');
    if (!clockEl) return;
    const now = new Date();
    const options = { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' };
    clockEl.innerText = now.toLocaleDateString('en-IN', options).replace(',', ' •');
}

document.addEventListener("DOMContentLoaded", () => {
    fetchData();
    setInterval(fetchData, 60000); // Refresh data every minute
    
    updateClock();
    setInterval(updateClock, 1000); // Update clock every second
});

let globalData = [];
let currentTab = 'nifty50'; // 'nifty50', 'fo', 'gainers', 'losers'
let lastTab = null;

async function fetchData() {
    try {
        const response = await fetch('/api/data?t=' + new Date().getTime());
        const json = await response.json();
        
        if (json && json.data) {
            // Filter out non-stocks or indices if needed, but the API gives F&O specific list
            globalData = json.data.map(d => ({
                symbol: d.symbol,
                pChange: d.pChange || 0,
                lastPrice: d.lastPrice || 0,
                volume: d.totalTradedVolume || 0,
                value: d.totalTradedValue || (d.lastPrice * d.totalTradedVolume) || 1, // fallback to 1 to avoid zero area
                isNifty50: d.isNifty50 || false
            }));
            
            updateBadges();
            renderHeatmap();
        } else {
            document.getElementById('loading').innerText = "Failed to load data structure.";
        }
    } catch (error) {
        console.error("Error fetching data:", error);
        const loadingEl = document.getElementById('loading');
        if (loadingEl) {
            loadingEl.innerText = "Error: " + error.message;
        }
    }
}

function updateBadges() {
    const gainers = globalData.filter(d => d.pChange > 0);
    const losers = globalData.filter(d => d.pChange < 0);
    const nifty50 = globalData.filter(d => d.isNifty50);
    
    const badgeNifty50 = document.getElementById('badge-nifty50');
    if (badgeNifty50) badgeNifty50.innerText = nifty50.length;

    const badgeFo = document.getElementById('badge-fo') || document.getElementById('badge-all') || document.getElementById('badge-turnover');
    if (badgeFo) badgeFo.innerText = globalData.length;
    
    const badgeGainers = document.getElementById('badge-gainers');
    if (badgeGainers) badgeGainers.innerText = gainers.length;
    
    const badgeLosers = document.getElementById('badge-losers');
    if (badgeLosers) badgeLosers.innerText = losers.length;
}

document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', (e) => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        e.currentTarget.classList.add('active');
        const text = e.currentTarget.innerText.toLowerCase();
        
        if (text.includes('gainers')) currentTab = 'gainers';
        else if (text.includes('losers')) currentTab = 'losers';
        else if (text.includes('nifty 50')) currentTab = 'nifty50';
        else currentTab = 'fo';
        
        renderHeatmap();
    });
});

function renderHeatmap() {
    const container = document.getElementById('heatmap-container');
    
    // Completely wipe the DOM on every single data fetch
    // This ensures the entry animation replays every 60 seconds, acting as a visual refresh indicator
    container.innerHTML = '';
    lastTab = currentTab;
    
    container.style.height = ''; // clear inline height to prevent scrolling
    
    const width = container.clientWidth - 4;
    const height = container.clientHeight - 4;
    
    if (width === 0 || height === 0) return; // container not ready

    // Filter data based on tab
    let displayData = globalData;
    if (currentTab === 'nifty50') {
        displayData = globalData.filter(d => d.isNifty50);
    } else if (currentTab === 'gainers') {
        displayData = globalData.filter(d => d.pChange > 0);
    } else if (currentTab === 'losers') {
        displayData = globalData.filter(d => d.pChange < 0);
    }

    // Sort all display data by pChange descending so Gainers appear at top-left and Losers at bottom-right
    displayData.sort((a, b) => {
        const pA = a.pChange !== undefined ? a.pChange : 0;
        const pB = b.pChange !== undefined ? b.pChange : 0;
        return pB - pA;
    });
    
    const total = displayData.length;
    if (total === 0) return;

    const colorScaleGreen = d3.scaleLinear().domain([0, 1, 2.5]).range(["#ffcc00", "#8ab734", "#1a6e25"]).clamp(true);
    const colorScaleRed = d3.scaleLinear().domain([0, -1, -2.5]).range(["#ffcc00", "#ff4500", "#8b0000"]).clamp(true);
    
    const combinedColorScale = (pChange) => {
        return pChange >= 0 ? colorScaleGreen(pChange) : colorScaleRed(pChange);
    };

    if (displayData.length > 0) {
        renderSubTreemap(container, displayData, 0, 0, width, height, combinedColorScale, true);
    }
}

function renderSubTreemap(container, data, xOffset, yOffset, width, height, colorScale, isGainer) {
    // Sort data to ensure top gainers are top-left, top losers are bottom-right
    data.sort((a, b) => {
        const pA = a.pChange !== undefined ? a.pChange : 0;
        const pB = b.pChange !== undefined ? b.pChange : 0;
        return pB - pA;
    });

    const targetAspectRatio = 1.6; 
    const N = data.length;
    
    let cols = Math.ceil(Math.sqrt(N * (width / height) / targetAspectRatio));
    cols = Math.max(1, cols);
    let rows = Math.ceil(N / cols);
    
    while (cols * rows < N) {
        cols++;
        rows = Math.ceil(N / cols);
    }

    // Configure container for native CSS Grid
    d3.select(container)
        .style("display", "grid")
        .style("grid-template-columns", `repeat(${cols}, 1fr)`)
        .style("grid-template-rows", `repeat(${rows}, 1fr)`)
        .style("gap", "1px")
        .style("background-color", "#ffffff")
        .style("padding", "0px");

    const nodes = d3.select(container)
        .selectAll(".node") 
        .data(data, d => d.symbol); // Key by symbol for smart updates

    const nodesEnter = nodes.enter()
        .append("div")
        .attr("class", "node")
        .style("position", "relative") // Override previous absolute CSS if any
        .style("width", "100%")
        .style("height", "100%")
        // Add a stunning diagonal wave entry animation
        .style("animation", "popIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) backwards")
        .style("animation-delay", (d, i) => `${(i % cols) * 20 + Math.floor(i / cols) * 20}ms`)
        .on("click", function(event, d) {
            let tvSymbol = d.symbol;
            if (tvSymbol === "NIFTY 50") tvSymbol = "NIFTY";
            else if (tvSymbol === "BANK NIFTY") tvSymbol = "BANKNIFTY";
            else if (tvSymbol === "FIN NIFTY") tvSymbol = "FINNIFTY";
            else if (tvSymbol === "MIDCAP NIFTY") tvSymbol = "MIDCPNIFTY";
            
            const encodedSymbol = encodeURIComponent(tvSymbol);
            const url = `https://in.tradingview.com/chart/NQHbNLlp/?symbol=NSE%3A${encodedSymbol}`;
            window.open(url, '_blank');
        });

    // Create the text elements only for newly entering nodes
    nodesEnter.append("div").attr("class", "symbol");
    nodesEnter.append("div").attr("class", "change");

    // Merge new and existing nodes to update them all
    const allNodes = nodesEnter.merge(nodes);

    allNodes
        .style("grid-column", (d, i) => {
            if (i === data.length - 1) {
                const itemsInLastRow = data.length % cols || cols;
                if (itemsInLastRow < cols) {
                    const span = cols - itemsInLastRow + 1;
                    return `span ${span}`;
                }
            }
            return "span 1";
        })
        .style("background-color", d => colorScale(d.pChange))
        .style("color", d => Math.abs(d.pChange) < 1.5 ? "#222" : "#fff")
        .style("text-shadow", d => Math.abs(d.pChange) < 1.5 ? "none" : "0px 1px 2px rgba(0,0,0,0.5)")
        .attr("title", d => `${d.symbol}\nPrice: ₹${d.lastPrice}\nChange: ${d.pChange.toFixed(2)}%`);

    const baseNodeWidth = width / cols;
    const baseNodeHeight = height / rows;

    allNodes.each(function(d, i) {
        let nodeWidth = baseNodeWidth;
        if (i === data.length - 1) {
            const itemsInLastRow = data.length % cols || cols;
            if (itemsInLastRow < cols) {
                const span = cols - itemsInLastRow + 1;
                nodeWidth = baseNodeWidth * span;
            }
        }
        const nodeHeight = baseNodeHeight;
        
        // Use select instead of append to update existing text
        d3.select(this).select(".symbol")
            .text(d.symbol)
            .style("font-size", () => {
                const minDim = Math.min(nodeWidth, nodeHeight);
                if (minDim < 20) return "6px";
                if (minDim < 35) return "8px";
                if (minDim > 100) return "14px";
                return "10px";
            });
            
        const sign = d.pChange > 0 ? "+" : "";
        d3.select(this).select(".change")
            .text(`${sign}${d.pChange.toFixed(2)}%`)
            .style("font-size", () => {
                const minDim = Math.min(nodeWidth, nodeHeight);
                if (minDim < 20) return "5px";
                if (minDim < 35) return "7px";
                if (minDim > 100) return "12px";
                return "9px";
            })
            .style("display", nodeHeight < 25 ? "none" : "block");
    });
    
    // Remove any extra nodes
    nodes.exit().remove();
}

window.addEventListener('resize', () => {
    if (globalData.length > 0) {
        renderHeatmap();
    }
});
