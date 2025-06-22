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
      const articles = block.querySelectorAll('.article');
      articles.forEach(article => {
        const match = article.innerText.toLowerCase().includes(keyword);
        article.style.display = match ? 'block' : 'none';
        if (match) hasVisible = true;
      });
      block.style.display = hasVisible ? 'block' : 'none';
    });
  });

  filterCategory('all');
});

function showArticleModal(title, date, image, content) {
  document.getElementById('modalTitle').innerText = title;
  document.getElementById('modalDate').innerText = date;
  document.getElementById('modalImage').src = image;
  document.getElementById('modalContent').innerText = content;
  document.getElementById('articleModal').classList.add('active');
}
function closeModal() {
  document.getElementById('articleModal').classList.remove('active');
}
document.getElementById('articleModal').onclick = function(e) {
  if (e.target === this) closeModal();
};
const backToTopBtn = document.getElementById('backToTop');
window.onscroll = () => {
  backToTopBtn.style.display = (window.scrollY > 200) ? 'block' : 'none';
};
backToTopBtn.onclick = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
};