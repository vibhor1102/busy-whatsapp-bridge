// First, let's see what happens when we trigger the dropdown
const placeholder = document.getElementById('react-select-2-placeholder');

// Store all current divs count
const beforeCount = document.querySelectorAll('div').length;

// Trigger dropdown
placeholder.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));

// Check after a moment
setTimeout(() => {
  const afterCount = document.querySelectorAll('div').length;
  console.log('Divs before:', beforeCount, 'after:', afterCount);
  
  // Get the last few divs added (React Select usually appends to body)
  const allDivs = document.querySelectorAll('div');
  const lastDivs = Array.from(allDivs).slice(-5);
  
  console.log('\nLast 5 divs in DOM:');
  lastDivs.forEach((div, i) => {
    console.log(i, div.className || '[no class]', div.textContent.substring(0, 50));
  });
  
  // Look for portal/root containers
  const portals = document.querySelectorAll('[id*="portal"], [class*="portal"]');
  console.log('\nPortal elements found:', portals.length);
  portals.forEach(p => console.log(p.className, p.children.length));
}, 1000);
