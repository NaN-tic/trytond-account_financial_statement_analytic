#:after:account/account:section:otras_tareas_contables#

=====================================================================
Contabilidad analítica en balance de situación y pérdidas y ganancias
=====================================================================
.. Modulo account_financial_statement_analytic

Podemos ver nuestros informes de balance de situación y pérdidas y ganancias 
filtrados por una cuenta analítica. El proceso es muy semejante al del balance 
de situación y pérdidas y ganancias que se explica en el *Balance de situación 
y pérdidas y ganancias*. 

Así una vez creado el informe, veremos que nos aparece el campo cuenta analítica 
al lado de la empresa. 

.. tal como muestra la siguiente imagen (informe de balances contables)
Si seleccionamos alguna cuenta, esta se aplicará como filtro para el cálculo de 
los valores, teniendo en cuenta sólo aquellos apuntes que tengan un movimiento 
analítico en la cuenta seleccionada o alguna de sus cuentas hijas. Por ejemplo, 
si tenemos la siguiente estructura:

 * Centros de coste
 
    * Centro de coste 1
    
    * Centro de coste 2
    
 * Proyectos
 
    * Proyecto 1
    
    * Proyecto 2

Si seleccionamos la cuenta Centro de coste 1, sólo se tendrán en cuenta 
aquellos apuntes que estén asignados a la cuenta Centro de coste 1.

Si seleccionamos la cuenta Centros de coste, se tendrán en cuenta sólo aquellos 
apuntes, que estén asignados a las cuentas: Centros de coste, Centro de coste 1, 
Centro de coste 2.

Si un apunte está asignado a múltiples cuentas analíticas, se tendrá en cuenta 
siempre que alguna de ellas cumpla con el filtro seleccionado. 