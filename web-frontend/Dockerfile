# Nginx image for serving static files
FROM nginx:alpine

# Copy the web files to nginx directory
COPY index.html /usr/share/nginx/html/
COPY js/ /usr/share/nginx/html/js/

# Copy optional directories if they exist (using a workaround for conditional copy)
# Create empty directories if needed
RUN mkdir -p /usr/share/nginx/html/css /usr/share/nginx/html/assets

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"] 