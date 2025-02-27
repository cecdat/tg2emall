FROM php:7.4-apache

RUN apt-get update && apt-get install -y \
    libpng-dev libjpeg-dev libfreetype6-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install pdo_mysql gd \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN a2enmod rewrite

COPY .htaccess /var/www/html/.htaccess

# 创建缓存目录并设置权限
RUN mkdir -p /var/www/html/content/cache \
    && chown -R www-data:www-data /var/www/html/content \
    && chmod -R 755 /var/www/html/content

WORKDIR /var/www/html

RUN chown www-data:www-data .htaccess && chmod 644 .htaccess
RUN sed -i 's/AllowOverride None/AllowOverride All/' /etc/apache2/apache2.conf

CMD ["apache2-foreground"]
