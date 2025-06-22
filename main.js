document.addEventListener('DOMContentLoaded', () => {
  const buttons = document.querySelectorAll('.nav-btn');
  const categoryBlocks = document.querySelectorAll('.category-block');
  const searchInput = document.getElementById('searchInput');

  function filterCategory(category) {
    categoryBlocks.forEach(block => {
      const match = category === 'all' || block.dataset.category === category;
      block.style.display = match ? 'block' : 'none';
    });
  }

  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      filterCategory(btn.dataset.category);
      searchInput.value = '';
    });
  });

  searchInput.addEventListener('input', () => {
    const keyword = searchInput.value.toLowerCase();
    categoryBlocks.forEach(block => {
      let hasVisible = false;
      const items = block.querySelectorAll('.grid-item');
      items.forEach(item => {
        const match = item.innerText.toLowerCase().includes(keyword);
        item.style.display = match ? 'block' : 'none';
        if (match) hasVisible = true;
      });
      block.style.display = hasVisible ? 'block' : 'none';
    });
  });

  filterCategory('all');
});

function openImage(src) {
  const modal = document.getElementById('imgModal');
  const img = document.getElementById('modalImg');
  img.src = src;
  modal.style.display = 'flex';
}
function closeImage() {
  document.getElementById('imgModal').style.display = 'none';
}
