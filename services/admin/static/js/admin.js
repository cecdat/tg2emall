/**
 * 后台管理系统公共JS
 */

$(document).ready(function() {
    // 初始化工具提示
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // 初始化弹窗
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // 自动隐藏警告框
    setTimeout(function() {
        $('.alert').fadeOut();
    }, 5000);

    // 确认对话框
    window.confirmAction = function(message, callback) {
        if (confirm(message)) {
            callback();
        }
    };

    // AJAX请求通用处理
    window.handleAjaxRequest = function(options) {
        var defaults = {
            type: 'GET',
            dataType: 'json',
            cache: false,
            beforeSend: function() {
                // 可以显示加载动画
            },
            error: function(xhr, status, error) {
                console.error('AJAX Error:', error);
                alert('网络错误，请重试。');
            }
        };
        
        return $.ajax($.extend(defaults, options));
    };

    // 格式化时间
    window.formatDateTime = function(dateTimeString) {
        if (!dateTimeString) return '';
        var date = new Date(dateDateTimeString);
        return date.toLocaleString('zh-CN');
    };

    // 表格行高亮
    $('.table tbody tr').hover(
        function() {
            $(this).addClass('table-active');
        },
        function() {
            $(this).removeClass('table-active');
        }
    );

    // 表格排序功能
    $('table[data-sortable="true"] th[data-sort]').click(function() {
        var column = $(this).data('sort');
        var direction = $(this).data('direction') || 'asc';
        
        // 切换排序方向
        if ($(this).hasClass('sort-asc')) {
            direction = 'desc';
            $(this).removeClass('sort-asc').addClass('sort-desc');
        } else {
            direction = 'asc';
            $(this).removeClass('sort-desc').addClass('sort-asc');
        }
        
        // 更新所有排序列样式
        $(this).siblings().removeClass('sort-asc sort-desc');
        
        // 发送排序请求
        var url = window.location.href.split('?')[0];
        var params = new URLSearchParams(window.location.search);
        params.set('sort', column);
        params.set('order', direction);
        
        window.location.href = url + '?' + params.toString();
    });

    // 表单验证增强
    $('form[data-validate="true"]').submit(function(e) {
        var form = $(this);
        var isValid = true;
        
        // 必填字段检查
        form.find('[required]').each(function() {
            if ($(this).val().trim() === '') {
                $(this).addClass('is-invalid');
                isValid = false;
            } else {
                $(this).removeClass('is-invalid');
            }
        });
        
        if (!isValid) {
            e.preventDefault();
            alert('请填写所有必填字段。');
            return false;
        }
    });

    // 字符计数
    $('[data-max-length]').each(function() {
        var maxLength = parseInt($(this).data('max-length'));
        var counter = $('<small class="text-muted float-end"></small>');
        $(this).after(counter);
        
        function updateCounter() {
            var length = $(this).val().length;
            var remaining = maxLength - length;
            counter.text(length + '/' + maxLength);
            
            if (remaining < 0) {
                counter.addClass('text-danger');
            } else if (remaining < 10) {
                counter.addClass('text-warning');
            } else {
                counter.removeClass('text-danger text-warning');
            }
        }
        
        $(this).on('input', updateCounter);
        updateCounter.call($(this)[0]);
    });

    // 复制到剪贴板
    window.copyToClipboard = function(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(function() {
                toast('复制成功！');
            });
        } else {
            // 降级方案
            var textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            toast('复制成功！');
        }
    };

    // Toast 通知
    window.toast = function(message, type = 'info') {
        var alertClass = 'alert-' + type;
        var toast = $('<div class="alert ' + alertClass + ' alert-dismissible fade show position-fixed" style="top: 20px; right: 20px; z-index: 9999;"><i class="fas fa-' + getIcon(type) + ' me-2"></i>' + message + '<button type="button" class="btn-close" data-bs-dismiss="alert"></button></div>');
        
        $('body').append(toast);
        
        setTimeout(function() {
            toast.fadeOut(function() {
                toast.remove();
            });
        }, 3000);
    };

    function getIcon(type) {
        var icons = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    // 防抖函数
    window.debounce = function(func, wait, immediate) {
        var timeout;
        return function() {
            var context = this, args = arguments;
            var later = function() {
                timeout = null;
                if (!immediate) func.apply(context, args);
            };
            var callNow = immediate && !timeout;
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
            if (callNow) func.apply(context, args);
        };
    };

    // 节流函数
    window.throttle = function(func, limit) {
        var inThrottle;
        return function() {
            var args = new arguments;
            var context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        }
    };

    // 搜索建议
    $('[data-search-suggestions]').on('input', debounce(function() {
        var $input = $(this);
        var query = $input.val();
        
        if (query.length < 2) return;
        
        $.ajax({
            url: '/api/admin/search-suggestions',
            data: { q: query, type: $input.data('search-suggestions') },
            success: function(data) {
                if (data.success && data.suggestions.length > 0) {
                    showSuggestions($input, data.suggestions);
                } else {
                    hideSuggestions($input);
                }
            }
        });
    }, 300));

    function showSuggestions($input, suggestions) {
        hideSuggestions($input);
        
        var suggestionsList = $('<ul class="list-group position-absolute suggestions-list"></ul>');
        
        suggestions.forEach(function(suggestion) {
            suggestionsList.append('<li class="list-group-item suggestion-item cursor-pointer">' + suggestion + '</li>');
        });
        
        $input.after(suggestionsList);
        
        $('.suggestion-item').click(function() {
            $input.val($(this).text());
            hideSuggestions($input);
            $input.closest('form').submit();
        });
    }

    function hideSuggestions($input) {
        $input.siblings('.suggestions-list').remove();
    }

    // 点击外部隐藏建议
    $(document).click(function(e) {
        if (!$(e.target).closest('[data-search-suggestions]').length) {
            $('.suggestions-list').remove();
        }
    });

    // 全选/取消全选
    $('#select-all').change(function() {
        $('input[type="checkbox"][name="item_ids[]"]').prop('checked', this.checked);
    });

    // 批量操作
    $('.batch-action').click(function() {
        var action = $(this).data('action');
        var selectedItems = $('input[type="checkbox"][name="item_ids[]"]:checked');
        
        if (selectedItems.length === 0) {
            alert('请选择要操作的项目。');
            return;
        }
        
        if (confirm('确定要对选中的 ' + selectedItems.length + ' 个项目执行 ' + action + ' 操作吗？')) {
            var ids = selectedItems.map(function() { return $(this).val(); }).get();
            
            $.ajax({
                url: '/api/admin/batch-action',
                method: 'POST',
                data: { action: action, ids: ids },
                success: function(data) {
                    if (data.success) {
                        toast('批量操作成功！', 'success');
                        location.reload();
                    } else {
                        toast('批量操作失败：' + data.message, 'error');
                    }
                },
                error: function() {
                    toast('网络错误，请重试。', 'error');
                }
            });
        }
    });

    console.log('后台管理系统JS初始化完成');
});
