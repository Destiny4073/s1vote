// 类别映射
const categoryMap = {
    'TV': { name: 'TV', class: 'tv-tag' },
    'MOV': { name: 'MOVIE', class: 'movie-tag' },
    'OVA': { name: 'OVA', class: 'ova-tag' },
    'WEB': { name: 'WEB', class: 'web-tag' }
};

// 争议等级映射
const controversyMap = {
    'low': { text: '全员一致', class: 'low-controversy', max: 0.5 },
    'medium': { text: '略有分歧', class: 'medium-controversy', max: 1 },
    'high': { text: '褒贬不一', class: 'high-controversy', max: 1.5 },
    'very-high': { text: '你死我活', class: 'very-high-controversy', max: 2 }
};

// 处理后的作品数据
let movieData = [];
let filteredData = [];
let currentPage = 1;
const pageSize = 20;

// 当前排序状态
let sortField = 'score';
let sortDirection = 'desc';
let currentSortButton = 'good-btn';

// 当前筛选状态
let currentYear = 'all';
let currentMonth = 'all';
let currentSearchTerm = '';
let currentCategories = ['TV', 'MOV', 'OVA', 'WEB'];

// 页面加载时获取数据
document.addEventListener('DOMContentLoaded', function () {
    // 获取数据
    fetch('database.min.json')
        .then(response => response.json())
        .then(data => {
            // 处理原始数据
            processMovieData(data);

            // 初始化数据
            filteredData = [...movieData];

            // 设置更新时间
            updateTime(data.update_time);

            // 填充年份和月份选项
            populateYearMonthOptions();

            // 更新类别选择显示
            updateSelectedCategories();

            // 应用默认排序
            applyCurrentSort();

            // 设置排序按钮事件
            document.getElementById('good-btn').addEventListener('click', function () {
                currentSortButton = 'good-btn';
                filterMovies();
            });

            document.getElementById('bad-btn').addEventListener('click', function () {
                currentSortButton = 'bad-btn';
                filterMovies();
            });

            document.getElementById('popular-btn').addEventListener('click', function () {
                currentSortButton = 'popular-btn';
                filterMovies();
            });

            document.getElementById('new-btn').addEventListener('click', function () {
                currentSortButton = 'new-btn';
                filterMovies();
            });

            document.getElementById('controversy-btn').addEventListener('click', function () {
                currentSortButton = 'controversy-btn';
                filterMovies();
            });

            // 设置筛选事件
            document.getElementById('year').addEventListener('change', function () {
                currentYear = this.value;
                filterMovies();
            });

            document.getElementById('month').addEventListener('change', function () {
                currentMonth = this.value;
                filterMovies();
            });

            // 设置搜索事件
            document.getElementById('search').addEventListener('input', function () {
                currentSearchTerm = this.value.toLowerCase();
                filterMovies();
            });

            // 类别下拉菜单事件
            document.getElementById('category-btn').addEventListener('click', function () {
                document.getElementById('category-options').classList.toggle('show');
            });

            // 类别选项改变事件
            document.querySelectorAll('.category-option input[type="checkbox"]').forEach(checkbox => {
                checkbox.addEventListener('change', function () {
                    if (this.checked) {
                        currentCategories.push(this.value);
                    } else {
                        const index = currentCategories.indexOf(this.value);
                        if (index > -1) {
                            currentCategories.splice(index, 1);
                        }
                    }
                    updateSelectedCategories();
                    filterMovies();
                });
            });

            // 点击其他地方关闭下拉菜单
            document.addEventListener('click', function (e) {
                if (!e.target.closest('.category-select')) {
                    document.getElementById('category-options').classList.remove('show');
                }
            });

            // 设置分页按钮事件
            setupPaginationControls();

            // 初始筛选
            filterMovies();
        })
        .catch(error => {
            console.error('数据加载失败：', error);
            const tableBody = document.getElementById('movie-table');
            tableBody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 40px; color: #e74a3b;">数据加载失败，请刷新重试</td></tr>`;
        });
});

// 处理原始作品数据
function processMovieData(data) {
    movieData = data.data.map(item => {
        // 计算投票总数
        const vote_count = parseInt(item.votes1) + parseInt(item.votes2) +
            parseInt(item.votes3) + parseInt(item.votes4) +
            parseInt(item.votes5);

        // 处理发布日期（只保留日期部分）
        const post_date = item.post_time.split(' ')[0];

        // 获取争议等级
        const std = parseFloat(item.standard_deviation);
        let controversyLevel = 'low';
        if (std <= controversyMap.low.max) controversyLevel = 'low';
        else if (std <= controversyMap.medium.max) controversyLevel = 'medium';
        else if (std <= controversyMap.high.max) controversyLevel = 'high';
        else controversyLevel = 'very-high';

        return {
            ...item,
            vote_count: vote_count,
            post_date: post_date,
            score: parseFloat(item.score),
            standard_deviation: std,
            controversy_level: controversyLevel
        };
    }).filter(item => item.year && item.month && item.category); // 排除无效数据
}

// 填充年份和月份选项
function populateYearMonthOptions() {
    // 获取所有年份
    const years = [...new Set(movieData.map(item => item.year))].sort((a, b) => b - a);
    const yearSelect = document.getElementById('year');
    yearSelect.innerHTML = '<option value="all">全部年份</option>';
    years.forEach(year => {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = `${year}年`;
        yearSelect.appendChild(option);
    });

    // 月份选项（季节）
    const monthSelect = document.getElementById('month');
    const seasonOptions = [
        { value: "1", text: "1月" },
        { value: "4", text: "4月" },
        { value: "7", text: "7月" },
        { value: "10", text: "10月" }
    ];

    monthSelect.innerHTML = '<option value="all">全部月份</option>';
    seasonOptions.forEach(season => {
        const option = document.createElement('option');
        option.value = season.value;
        option.textContent = season.text;
        monthSelect.appendChild(option);
    });
}

// 更新已选类别显示
function updateSelectedCategories() {
    const container = document.getElementById('selected-categories');
    container.innerHTML = '';

    // 如果没有选中任何类别，显示提示
    if (currentCategories.length === 0) {
        container.innerHTML = '<span style="color:#e74a3b;">未选择</span>';
        return;
    }

    // 如果选中了所有类别，显示"全部类别"
    if (currentCategories.length === 4) {
        container.innerHTML = '<span>全部类别</span>';
        return;
    }

    // 显示选中的类别标签
    currentCategories.forEach(category => {
        const element = document.createElement('span');
        element.className = 'selected-category';
        element.style.backgroundColor = category === 'TV' ? '#4e73df' :
            category === 'MOV' ? '#1cc85e' :
                category === 'OVA' ? '#f6c23e' : '#9b59b6';
        element.innerHTML = `${categoryMap[category]?.name || category}`;
        container.appendChild(element);
    });
}

// 渲染作品表格
function renderMovieTable() {
    const tableBody = document.getElementById('movie-table');
    tableBody.innerHTML = '';

    if (filteredData.length === 0) {
        const row = document.createElement('tr');
        row.innerHTML = `<td colspan="8" style="text-align: center; padding: 40px; color: #5a5c69;">未找到匹配的作品</td>`;
        tableBody.appendChild(row);
        document.getElementById('result-count').textContent = '0';
        updatePagination();
        return;
    }

    // 计算当前页的数据
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = Math.min(startIndex + pageSize, filteredData.length);
    const currentData = filteredData.slice(startIndex, endIndex);

    currentData.forEach((movie, index) => {
        const row = document.createElement('tr');

        // 根据分数决定颜色
        const scoreClass = movie.score >= 0 ? 'positive-score' : 'negative-score';

        // 争议级别
        const controversyInfo = controversyMap[movie.controversy_level];

        // 类别信息
        const categoryInfo = categoryMap[movie.category] || { name: movie.category, class: 'movie-tag' };

        // 创建标题链接
        const titleLink = document.createElement('a');
        titleLink.href = `https://stage1st.com/2b/thread-${movie.tid}-1-1.html`;
        titleLink.target = '_blank';
        titleLink.textContent = movie.title;

        // 截断平均分小数部分
        const truncatedScore = Math.trunc(movie.score);

        row.innerHTML = `
    <td class="rank">${startIndex + index + 1}</td>
    <td class="movie-title">
<span class="category-tag ${categoryInfo.class}">${categoryInfo.name}</span>
    </td>
    <td class="score ${scoreClass}">${truncatedScore}</td>
    <td class="votes">${formatNumber(movie.vote_count)}</td>
    <td class="clicks">${formatNumber(movie.views)}</td>
    <td class="replies">${formatNumber(movie.replies)}</td>
    <td class="controversy">
<div class="controversy-tag ${controversyInfo.class}">
    ${controversyInfo.text}
</div>
<div class="controversy-bar">
    <div class="controversy-fill ${controversyInfo.class}" 
 style="width: ${Math.min(movie.standard_deviation / 2 * 100, 100)}%"></div>
</div>
    </td>
    <td class="date">${movie.post_date}</td>
`;

        // 将标题链接添加到标题单元格
        const titleCell = row.querySelector('.movie-title');
        titleCell.appendChild(titleLink);

        tableBody.appendChild(row);
    });

    // 更新结果计数
    document.getElementById('result-count').textContent = filteredData.length;

    // 更新分页控件
    updatePagination();
}

// 格式化数字（添加千位分隔符）
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// 筛选作品
function filterMovies() {
    // 初始化筛选数据
    filteredData = [...movieData];

    // 年份筛选
    if (currentYear !== 'all') {
        filteredData = filteredData.filter(movie => movie.year === currentYear);
    }

    // 月份筛选（按季节）
    if (currentMonth !== 'all') {
        const startMonth = parseInt(currentMonth);
        const endMonth = startMonth + 2;

        filteredData = filteredData.filter(movie => {
            const movieMonth = parseInt(movie.month);
            return movieMonth >= startMonth && movieMonth <= endMonth;
        });
    }

    // 类别筛选
    if (currentCategories.length === 0) {
        filteredData = [];
    } else {
        filteredData = filteredData.filter(movie => currentCategories.includes(movie.category));
    }

    // 搜索筛选（标题和别名）
    if (currentSearchTerm) {
        filteredData = filteredData.filter(movie => {
            // 检查标题是否匹配
            if (movie.title.toLowerCase().includes(currentSearchTerm)) {
                return true;
            }

            // 检查别名是否匹配
            if (movie.aliases && movie.aliases.length > 0) {
                return movie.aliases.some(alias =>
                    alias.toLowerCase().includes(currentSearchTerm)
                );
            }

            return false;
        });
    }

    // 特殊筛选规则：仅当满足以下全部条件时才排除投票数<30的作品
    const isYearAll = currentYear === 'all';
    const isMonthAll = currentMonth === 'all';
    const isNotNewSort = currentSortButton !== 'new-btn';
    const noSearchTerm = currentSearchTerm === '';
    const hasCategorySelected = currentCategories.length > 0;

    if (isYearAll && isMonthAll && noSearchTerm && hasCategorySelected && isNotNewSort) {
        filteredData = filteredData.filter(movie => movie.vote_count >= 30);
    }

    // 应用当前排序
    applyCurrentSort();

    // 重置到第一页
    currentPage = 1;
    renderMovieTable();
}

// 应用当前排序
function applyCurrentSort() {
    switch (currentSortButton) {
        case 'good-btn':
            sortMovies('score', 'desc');
            break;
        case 'bad-btn':
            sortMovies('score', 'asc');
            break;
        case 'popular-btn':
            sortMovies('vote_count', 'desc');
            break;
        case 'new-btn':
            sortMovies('tid', 'desc');
            break;
        case 'controversy-btn':
            sortMovies('standard_deviation', 'desc');
            break;
        default:
            sortMovies('score', 'desc');
    }
}

// 排序作品
function sortMovies(field, direction) {
    sortField = field;
    sortDirection = direction;

    // 更新当前排序按钮高亮
    updateSortButtonHighlight();

    // 执行排序
    filteredData.sort((a, b) => {
        let valueA, valueB;

        // 特殊处理tid排序（转换为数字）
        if (field === 'tid') {
            valueA = parseInt(a.tid);
            valueB = parseInt(b.tid);
        } else {
            valueA = a[field];
            valueB = b[field];
        }

        if (direction === 'asc') {
            return valueA > valueB ? 1 : -1;
        } else {
            return valueA < valueB ? 1 : -1;
        }
    });
}

// 更新排序按钮高亮状态
function updateSortButtonHighlight() {
    // 移除所有按钮的active类
    document.querySelectorAll('.sort-buttons .btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // 为当前按钮添加active类
    if (currentSortButton) {
        document.getElementById(currentSortButton).classList.add('active');
    }
}

// 更新时间显示
function updateTime(timestamp) {
    // 时间戳转换为北京时间（UTC+8）
    const beijingOffset = 8 * 60 * 60 * 1000; // 北京时间偏移
    const beijingTime = new Date(timestamp * 1000 + beijingOffset);

    const year = beijingTime.getUTCFullYear();
    const month = padZero(beijingTime.getUTCMonth() + 1);
    const day = padZero(beijingTime.getUTCDate());
    const hours = padZero(beijingTime.getUTCHours());
    const minutes = padZero(beijingTime.getUTCMinutes());
    const seconds = padZero(beijingTime.getUTCSeconds());

    const formattedTime = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
    document.getElementById('update-time').textContent = formattedTime;
}

// 补零函数
function padZero(num) {
    return num.toString().padStart(2, '0');
}

// 设置分页控件
function setupPaginationControls() {
    document.getElementById('first-page').addEventListener('click', function () {
        if (currentPage > 1) {
            currentPage = 1;
            renderMovieTable();
        }
    });

    document.getElementById('prev-page').addEventListener('click', function () {
        if (currentPage > 1) {
            currentPage--;
            renderMovieTable();
        }
    });

    document.getElementById('next-page').addEventListener('click', function () {
        const totalPages = Math.ceil(filteredData.length / pageSize);
        if (currentPage < totalPages) {
            currentPage++;
            renderMovieTable();
        }
    });

    document.getElementById('last-page').addEventListener('click', function () {
        const totalPages = Math.ceil(filteredData.length / pageSize);
        if (currentPage < totalPages) {
            currentPage = totalPages;
            renderMovieTable();
        }
    });
}

// 更新分页控件
function updatePagination() {
    const paginationContainer = document.getElementById('pagination');
    const totalPages = Math.ceil(filteredData.length / pageSize);

    // 清除页码按钮（保留首页、上一页、下一页、末页按钮）
    const pageButtons = paginationContainer.querySelectorAll('.page-num');
    pageButtons.forEach(button => button.remove());

    // 添加页码按钮
    const startPage = Math.max(1, Math.min(currentPage - 2, totalPages - 4));
    const endPage = Math.min(startPage + 4, totalPages);

    // 在上一页按钮之后插入页码按钮
    const prevButton = document.getElementById('prev-page');

    for (let i = startPage; i <= endPage; i++) {
        const pageButton = document.createElement('button');
        pageButton.className = `page-btn page-num ${i === currentPage ? 'active' : ''}`;
        pageButton.textContent = i;
        pageButton.addEventListener('click', function () {
            currentPage = i;
            renderMovieTable();
        });
        paginationContainer.insertBefore(pageButton, document.getElementById('next-page'));
    }

    // 更新按钮状态
    document.getElementById('first-page').disabled = currentPage === 1;
    document.getElementById('prev-page').disabled = currentPage === 1;
    document.getElementById('next-page').disabled = currentPage === totalPages || totalPages === 0;
    document.getElementById('last-page').disabled = currentPage === totalPages || totalPages === 0;
}