"""
SELECT

    c.first_name || ' ' || c.last_name AS customer_name,

    COUNT(DISTINCT o.order_id) AS total_orders,

    SUM(ol.quantity * ol.unit_price) AS total_spent,

    RANK() OVER (ORDER BY SUM(ol.quantity * ol.unit_price) DESC) AS customer_rank

FROM shopey.customers c

JOIN shopey.orders o

    ON c.customer_id = o.customer_id

JOIN shopey.order_lines ol

    ON o.order_id = ol.order_id

GROUP BY c.customer_id, c.first_name, c.last_name

HAVING COUNT(DISTINCT o.order_id) >= 1

ORDER BY customer_rank ASC;

"""