import pandas as pd
import streamlit as st
from PIL import Image
import requests
from io import BytesIO
import pymysql
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import base64


#Tạo một hàm để tạo table sau khi đọc được từ SQL
def show_grid(df, numeric_cols, height=500, theme = "blue" ):
    gb = GridOptionsBuilder.from_dataframe(df)

    for col in numeric_cols:
        gb.configure_column(col, type=["numericColumn", "customNumericFormat"], precision = 0, valueFormatter="x.toLocaleString()", aggFunc='sum',  enableValue=True )
    gb.configure_default_column(editable=False, filter=True, sortable=True, resizable=True)
    # Cho phép  hiện tổng ở dưới (footer)
    gb.configure_grid_options(
    groupIncludeFooter=True,
    groupIncludeTotalFooter=True,
    enableValue=True,
    showAggFuncs=True)

    gb.configure_side_bar()  # Thêm thanh filter bên phải (Excel-style)
    gridOptions = gb.build()
    # Hiển thị bảng AgGrid
    AgGrid(df, gridOptions=gridOptions, height=height, theme=theme)

# Tạo hàm căn giữa trang 
def center_page(text):
    st.markdown(f"<h3 style= 'text-align: center;'>{text}</h3>", unsafe_allow_html=True)



st.set_page_config(layout="wide")
pages = ["Core Agency" , "Elite", "Elite Đỗ Thị Lệ Hằng", "Elite Lê Đức Thành Long"]
selected_page = st.sidebar.radio("Chọn trang", pages)

conn = pymysql.connect(
    host="localhost",
    port=3306,
    user="root",
    password="123456789", 
    database="sale"       
    )
cursor = conn.cursor()

st.title("Báo cáo Doanh số hằng ngày")

# Inset Affina Image in report
url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRN8F-HkWgp0zQ8Kg3kpAYEdhTmqxbmIDxwEw&s"
response = requests.get(url)
img = Image.open(BytesIO(response.content))
buffered = BytesIO()  #dùng để ghi dữ liệu nhị phân và RAM thay vì lưu ra đĩa 
img.save(buffered, format= "PNG")
img_str = base64.b64encode(buffered.getvalue()).decode() #lấy dữ liệu nhị phân thành chuỗi văn bản 
st.image(img, width=150)

if selected_page == "Core Agency":
    #Create buttons to choose multiselection
    opt = st.multiselect("Chọn loại báo cáo: ", ['Details', 'DSA', 'BDM', 'BDD'])
    if 'Details' in opt:
        center_page("Chi tiết các đơn")
        detail = """
            with t1 as (
            select 
                dnsa.*, date(uadcd.`Ngày thanh toán`) as `Ngày thanh toán`, uadcd.`Code sale`, uadcd.`Sản phẩm`, uadcd.`Đối tác nhà bảo hiểm`, uadcd.`Số tiền thanh toán`, upper(uadcd.Channel) as `Channel Sales`, uadcd.`Loại bảo hiểm`
            from ds_nhan_su_affina dnsa 
            join union_all_data_cap_don uadcd on
            dnsa.`Điện thoại` = uadcd.`Code sale` 
            ),
            detail as (
            select
                Code,`Họ tên`, `Chức danh`, Channel,`Ngày thanh toán`,`Sản phẩm`,`Đối tác nhà bảo hiểm`,cast(`Số tiền thanh toán` as decimal) as `Số tiền thanh toán`,`QUẢN LÝ CẤP 1 (BDM)`,`QUẢN LÝ CẤP 2 (BDD)`,`Channel Sales`, `Thời gian bắt đầu`,`Loại bảo hiểm`
            from t1
            where 
                Channel = 'Core Agency' and 
                year(`Ngày thanh toán`) = year(now())
                and month(`Ngày thanh toán`) = month(now()))
            , 
            t2 as (
            select 
                Code,`Họ tên`, `Chức danh`,Channel,`Ngày thanh toán`,d.`Sản phẩm`,`Đối tác nhà bảo hiểm`,`QUẢN LÝ CẤP 1 (BDM)`, `QUẢN LÝ CẤP 2 (BDD)`,`Channel Sales`,
                `Thời gian bắt đầu`,`Loại bảo hiểm`, `Số tiền thanh toán`,	
                case when d.`Sản phẩm` LIKE '%Trách nhiệm Dân sự%' OR d.`Sản phẩm` LIKE '%vật chất xe Ô tô' THEN ROUND( d.`Số tiền thanh toán`/1.1, 0)
                    when d.`Sản phẩm` = 'Trách nhiệm sản phẩm' then ROUND( d.`Số tiền thanh toán`/1.05, 0) 
                else ROUND(d.`Số tiền thanh toán`, 0) end as 'Doanh thu trước thuế',
                rate_bonus, exchange_core
            from detail d
            left join qd dsqd on dsqd.provider = d.`Đối tác nhà bảo hiểm` and upper(dsqd.product) = upper(d.`Sản phẩm`)
            ),
            t3 as (
            select t2.*, 
            case when date(`Ngày thanh toán`) = CURDATE() then `Số tiền thanh toán` end as `Doanh số hôm nay`,
            (rate_bonus*`Doanh thu trước thuế`) as EST_Bonus,
            (exchange_core*`Doanh thu trước thuế`) as `Doanh số qui đổi`
            from t2
            )
            select Code, `Họ tên`, `Chức danh`, Channel, `Ngày thanh toán`, `Sản phẩm`, `Đối tác nhà bảo hiểm`, `QUẢN LÝ CẤP 1 (BDM)`, `QUẢN LÝ CẤP 2 (BDD)`, `Channel Sales`,
                `Thời gian bắt đầu`, `Loại bảo hiểm`, `Số tiền thanh toán`, `Doanh thu trước thuế`, `Doanh số qui đổi`, EST_Bonus
            from t3
    """
        cursor.execute(detail)  
        tables = cursor.fetchall()
        numeric_cols = ["Số tiền thanh toán", "Doanh thu trước thuế", "Doanh số qui đổi", "EST_Bonus"]
        columns = [col[0] for col in cursor.description]
        df = pd.DataFrame(tables, columns=columns)
        show_grid(df,numeric_cols )

    if 'DSA' in opt:
        center_page("Chi tiết báo cáo DSA ")
        detail = """
    with t1 as (
    select 
        dnsa.*, date(uadcd.`Ngày thanh toán`) as `Ngày thanh toán`, uadcd.`Code sale`, uadcd.`Sản phẩm`, uadcd.`Đối tác nhà bảo hiểm`, uadcd.`Số tiền thanh toán`, upper(uadcd.Channel) as `Channel Sales`, uadcd.`Loại bảo hiểm`
    from ds_nhan_su_affina dnsa 
    join union_all_data_cap_don uadcd on
    dnsa.`Điện thoại` = uadcd.`Code sale` 

    ),
    detail as (
    select
        Code,`Họ tên`, `Chức danh`, Channel,`Ngày thanh toán`,`Sản phẩm`,`Đối tác nhà bảo hiểm`,cast(`Số tiền thanh toán` as decimal) as `Số tiền thanh toán`,`QUẢN LÝ CẤP 1 (BDM)`,`QUẢN LÝ CẤP 2 (BDD)`,`Channel Sales`, `Thời gian bắt đầu`,`Loại bảo hiểm`
    from t1
    where 
        Channel = 'Core Agency' and 
        year(`Ngày thanh toán`) = year(now())
        and month(`Ngày thanh toán`) = month(now()) 
    )
    ,
    --  DSA 
    t2 as (
    select 
        Code,`Họ tên`, `Chức danh`, Channel,`Ngày thanh toán`,d.`Sản phẩm`,`Đối tác nhà bảo hiểm`,`QUẢN LÝ CẤP 1 (BDM)`,`QUẢN LÝ CẤP 2 (BDD)`,`Channel Sales`,`Thời gian bắt đầu`,`Loại bảo hiểm`, `Số tiền thanh toán`,	
        case when d.`Sản phẩm` LIKE '%Trách nhiệm Dân sự%' OR d.`Sản phẩm` LIKE '%vật chất xe Ô tô' THEN ROUND( d.`Số tiền thanh toán`/1.1, 0)
            when d.`Sản phẩm` = 'Trách nhiệm sản phẩm' then ROUND( d.`Số tiền thanh toán`/1.05, 0) 
        else ROUND(d.`Số tiền thanh toán`, 0) end as 'Doanh thu trước thuế',
        rate_bonus,exchange_core
    from detail d
    left join qd dsqd on dsqd.provider = d.`Đối tác nhà bảo hiểm` and upper(dsqd.product) = upper(d.`Sản phẩm`)
    ),
    t3 as (
    select t2.*, 
    case when date(`Ngày thanh toán`) = CURDATE() then `Số tiền thanh toán` end as `Doanh số hôm nay`,
    (rate_bonus*`Doanh thu trước thuế`) as EST_Bonus,
    (exchange_core*`Doanh thu trước thuế`) as `Doanh số qui đổi`
    from t2
    )
    -- select Code, `Họ tên`, `Chức danh`, Channel, `Ngày thanh toán`, `Sản phẩm`, `Đối tác nhà bảo hiểm`, `QUẢN LÝ CẤP 1 (BDM)`, `QUẢN LÝ CẤP 2 (BDD)`, `Channel Sales`,
    -- 	`Thời gian bắt đầu`, `Loại bảo hiểm`, `Số tiền thanh toán`, `Doanh thu trước thuế`, `Doanh số qui đổi`, EST_Bonus
    -- from t3
    ,
    -- -- Tracking DSA 
    DSA as (
    select Code, `Họ tên`, `Chức danh`, Channel, `Thời gian bắt đầu`, `QUẢN LÝ CẤP 1 (BDM)`, `QUẢN LÝ CẤP 2 (BDD)`, sum(`Số tiền thanh toán`) as `Số tiền thanh toán`,
        sum(`Doanh số qui đổi`) as `Doanh số qui đổi`, sum(`Doanh thu trước thuế`) as `Doanh thu trước thuế`, sum(`Doanh số hôm nay`) as `Doanh số hôm nay`, sum(EST_Bonus) as EST_Bonus
    from t3 
    group by 1,2,3,4,5,6,7
    )
    ,

    t6 as (
    select dnsa.Code, dnsa.`Họ tên`, dnsa.`Chức danh`, dnsa.Channel, dnsa.`QUẢN LÝ CẤP 1 (BDM)`, dnsa.`QUẢN LÝ CẤP 2 (BDD)`, DSA.`Số tiền thanh toán`, DSA.`Doanh số qui đổi`, DSA.`Doanh thu trước thuế`,DSA.`Doanh số hôm nay`, DSA.`EST_Bonus`
    from ds_nhan_su_affina dnsa 
    left join DSA  
        ON TRIM(DSA.`Họ tên`) = TRIM(dnsa.`Họ tên`)
    AND TRIM(DSA.Code) = TRIM(dnsa.Code)
    where (dnsa.`Chức danh` in ('DSA', 'Agency', 'BDM_DV'))  and (dnsa.`QUẢN LÝ CẤP 2 (BDD)` in ('TRẦN THỊ THÙY AN','NGUYỄN THỊ HỒNG LOAN','BÙI THỊ THỦY TIÊN' ))
    )
    select * from t6
    """
        cursor.execute(detail)  
        tables = cursor.fetchall()
        numeric_cols = ["Số tiền thanh toán", "Doanh thu trước thuế", "Doanh số qui đổi", "EST_Bonus"]
        columns = [col[0] for col in cursor.description]
        df = pd.DataFrame(tables, columns=columns)
        show_grid(df,numeric_cols )
    if 'BDM' in opt:
        center_page("Chi tiết báo cáo BDM ")
        detail = """
        with t1 as (
        select 
            dnsa.*, date(uadcd.`Ngày thanh toán`) as `Ngày thanh toán`, uadcd.`Code sale`, uadcd.`Sản phẩm`, uadcd.`Đối tác nhà bảo hiểm`, uadcd.`Số tiền thanh toán`, upper(uadcd.Channel) as `Channel Sales`, uadcd.`Loại bảo hiểm`
        from ds_nhan_su_affina dnsa 
        join union_all_data_cap_don uadcd on
        dnsa.`Điện thoại` = uadcd.`Code sale` 

        ),
        detail as (
        select
            Code,`Họ tên`, `Chức danh`, Channel,`Ngày thanh toán`,`Sản phẩm`,`Đối tác nhà bảo hiểm`,cast(`Số tiền thanh toán` as decimal) as `Số tiền thanh toán`,`QUẢN LÝ CẤP 1 (BDM)`,`QUẢN LÝ CẤP 2 (BDD)`,`Channel Sales`, `Thời gian bắt đầu`,`Loại bảo hiểm`
        from t1
        where 
            Channel = 'Core Agency' and 
            year(`Ngày thanh toán`) = year(now())
            and month(`Ngày thanh toán`) = month(now())
        )
        ,
        --  DSA 
        t2 as (
        select 
            Code,`Họ tên`, `Chức danh`, Channel,`Ngày thanh toán`,d.`Sản phẩm`,`Đối tác nhà bảo hiểm`,`QUẢN LÝ CẤP 1 (BDM)`,`QUẢN LÝ CẤP 2 (BDD)`,`Channel Sales`,`Thời gian bắt đầu`,`Loại bảo hiểm`, `Số tiền thanh toán`,	
            case when d.`Sản phẩm` LIKE '%Trách nhiệm Dân sự%' OR d.`Sản phẩm` LIKE '%BHVCOTO%' THEN ROUND( d.`Số tiền thanh toán`/1.1, 0)
                when d.`Sản phẩm` = 'Trách nhiệm sản phẩm' then ROUND( d.`Số tiền thanh toán`/1.05, 0) 
            else ROUND(d.`Số tiền thanh toán`, 0) end as 'Doanh thu trước thuế',
            rate_bonus, exchange_core
        from detail d
        left join qd dsqd on dsqd.provider = d.`Đối tác nhà bảo hiểm` and upper(dsqd.product) = upper(d.`Sản phẩm`)
        ),
        t3 as (
        select t2.*, 
        case when date(`Ngày thanh toán`) = CURDATE() then `Số tiền thanh toán` end as `Doanh số hôm nay`,
        (rate_bonus*`Doanh thu trước thuế`) as EST_Bonus,
        (exchange_core*`Doanh thu trước thuế`) as `Doanh số qui đổi`
        from t2
        ),
        DSA as (
        select Code, `Họ tên`, `Chức danh`, Channel, `Thời gian bắt đầu`, `QUẢN LÝ CẤP 1 (BDM)`, `QUẢN LÝ CẤP 2 (BDD)`, sum(`Số tiền thanh toán`) as `Số tiền thanh toán`,
            sum(`Doanh số qui đổi`) as `Doanh số qui đổi`, sum(`Doanh thu trước thuế`) as `Doanh thu trước thuế`, sum(`Doanh số hôm nay`) as `Doanh số hôm nay`, sum(EST_Bonus) as EST_Bonus
        from t3 
        group by 1,2,3,4,5,6,7
        )
        ,

        t6 as (
        select dnsa.Code, dnsa.`Họ tên`, dnsa.`Chức danh`, dnsa.Channel, dnsa.`QUẢN LÝ CẤP 1 (BDM)`, dnsa.`QUẢN LÝ CẤP 2 (BDD)`, DSA.`Số tiền thanh toán`, DSA.`Doanh số qui đổi`, DSA.`Doanh thu trước thuế`,DSA.`Doanh số hôm nay`, DSA.`EST_Bonus`
        from ds_nhan_su_affina dnsa 
        left join DSA  
            ON TRIM(DSA.`Họ tên`) = TRIM(dnsa.`Họ tên`)
        AND TRIM(DSA.Code) = TRIM(dnsa.Code)
        where (dnsa.`Chức danh` in ('DSA', 'Agency', 'BDM_DV'))  and (dnsa.`QUẢN LÝ CẤP 2 (BDD)` in ('TRẦN THỊ THÙY AN','NGUYỄN THỊ HỒNG LOAN' ))
        )
        ,
        -- Tracking BDM_core
        t7 as (
        select 
        dnsa.Code, dnsa.`Họ tên`, dnsa.`Chức danh`, date(dnsa.`Thời gian bắt đầu`) as `Thời gian bắt đầu`, dnsa.`QUẢN LÝ CẤP 2 (BDD)`, sum(`Số tiền thanh toán`) as `Số tiền thanh toán`, coalesce(sum(`Doanh thu trước thuế`),0) as `Doanh thu trước thuế`, sum(`Doanh số qui đổi`) as `Doanh số qui đổi`, sum(EST_Bonus) as EST_Bonus,
        sum(`Doanh số hôm nay`) as `Doanh số hôm nay`
        from ds_nhan_su_affina dnsa
        left join DSA f on cast(f.`QUẢN LÝ CẤP 1 (BDM)` as binary) = cast(dnsa.`Họ tên` as binary)
        where (upper(dnsa.`Chức danh`)) like '%BDM%' 
        group by 1,2,3,4,5 
        ),
        t8 as (
        select t7.*,
            10 as `KPI tuyển dụng mới`,
            20 as `KPI DSA Active`,
            165000000 as `KPI Phí bảo hiểm qui đổi`,
            count(distinct case when dnsa.Status in ('A','P') and dnsa.`Chức danh` in ('DSA','Agency') then dnsa.Code end) as `Số DSA thực tế`,
            count(distinct case when dnsa.Status in ('A','P') and dnsa.`Chức danh` in ('DSA','Agency') and cast(dnsa.`Thời gian bắt đầu` as date) between '2025-04-01' and '2025-04-30' then dnsa.Code end) as `Tuyển dụng mới DSA`,
            count(distinct case when d.`Chức danh` not like '%BDM%' then d.Code end) as 'DSA Active'
        from t7
        join ds_nhan_su_affina dnsa on cast(dnsa.`QUẢN LÝ CẤP 1 (BDM)` as binary) = cast(t7.`Họ tên` as binary)
        left join DSA d on d.`QUẢN LÝ CẤP 1 (BDM)` = t7.`Họ tên`
        group by 1,2,3,4,5,6,7,8,9,10
        )
        ,
        BDM as (
        SELECT 
            a.*,
            (`Doanh số qui đổi` / 165000000)*0.6 AS `%_KPI doanh số qui đổi`,
            case when `Tuyển dụng mới DSA` >= 10 then 0.2 else `Tuyển dụng mới DSA`*0.2/`KPI tuyển dụng mới` end as `%_KPI tuyển dụng mới`,
            case when `DSA active` >= 20 or `DSA Active` / NULLIF(`Số DSA thực tế`, 0) >= 0.2 then 0.2 else `DSA Active` / NULLIF(`Số DSA thực tế`, 0)*0.1 end as `%_KPI DSA active`,
            b.`Tổng số tiền thanh toán tháng trước`,
            c.`Số tiền thanh toán cùng kì`
        FROM t8 AS a
        LEFT JOIN (
            SELECT 
                `QUẢN LÝ CẤP 1 (BDM)`, 
                SUM(`Số tiền thanh toán`) AS `Tổng số tiền thanh toán tháng trước`
            FROM t1
            WHERE 
                YEAR(`Ngày thanh toán`) = YEAR(NOW()) 
                AND MONTH(`Ngày thanh toán`) = MONTH(NOW()) - 1
            GROUP BY `QUẢN LÝ CẤP 1 (BDM)`
        ) AS b 
        ON b.`QUẢN LÝ CẤP 1 (BDM)` = a.`Họ tên`

        left join (
        SELECT `QUẢN LÝ CẤP 1 (BDM)`, SUM(`Số tiền thanh toán`) AS `Số tiền thanh toán cùng kì` FROM t1
        WHERE YEAR(`Ngày thanh toán`) = YEAR(NOW()) AND MONTH(`Ngày thanh toán`) = MONTH(NOW()) - 1 and day(`Ngày thanh toán`) <= day(now())
        GROUP BY `QUẢN LÝ CẤP 1 (BDM)`
        ) as c
        ON c.`QUẢN LÝ CẤP 1 (BDM)` = a.`Họ tên`
        )
        select *,(coalesce (`%_KPI doanh số qui đổi`,0) + coalesce (`%_KPI tuyển dụng mới`,0) + coalesce (`%_KPI DSA active`,0)) as `KPI tổng` from BDM
        where `QUẢN LÝ CẤP 2 (BDD)` != '0'
"""
        cursor.execute(detail)  
        tables = cursor.fetchall()
        numeric_cols = ["Số tiền thanh toán", "Doanh thu trước thuế", "Doanh số qui đổi", "EST_Bonus"]
        columns = [col[0] for col in cursor.description]
        df = pd.DataFrame(tables, columns=columns)
        show_grid(df,numeric_cols )
    if 'BDD' in opt:
        center_page("Chi tiết báo cáo BDD ")
        detail = """ 
        with t1 as (
        select 
            dnsa.*, date(uadcd.`Ngày thanh toán`) as `Ngày thanh toán`, uadcd.`Code sale`, uadcd.`Sản phẩm`, uadcd.`Đối tác nhà bảo hiểm`, uadcd.`Số tiền thanh toán`, upper(uadcd.Channel) as `Channel Sales`, uadcd.`Loại bảo hiểm`
        from ds_nhan_su_affina dnsa 
        join union_all_data_cap_don uadcd on
        dnsa.`Điện thoại` = uadcd.`Code sale` 

        ),
        detail as (
        select
            Code,`Họ tên`, `Chức danh`, Channel,`Ngày thanh toán`,`Sản phẩm`,`Đối tác nhà bảo hiểm`,cast(`Số tiền thanh toán` as decimal) as `Số tiền thanh toán`,`QUẢN LÝ CẤP 1 (BDM)`,`QUẢN LÝ CẤP 2 (BDD)`,`Channel Sales`, `Thời gian bắt đầu`,`Loại bảo hiểm`
        from t1
        where 
            Channel = 'Core Agency' and 
            year(`Ngày thanh toán`) = year(now())
            and month(`Ngày thanh toán`) = month(now())
        )
        ,
        --  DSA 
        t2 as (
        select 
            Code, `Họ tên`, `Chức danh`, Channel, `Ngày thanh toán`, d.`Sản phẩm`, `Đối tác nhà bảo hiểm`, `QUẢN LÝ CẤP 1 (BDM)`, `QUẢN LÝ CẤP 2 (BDD)`, `Channel Sales`, `Thời gian bắt đầu`, `Loại bảo hiểm`, `Số tiền thanh toán`,	
            case when d.`Sản phẩm` LIKE '%Trách nhiệm Dân sự%' OR d.`Sản phẩm` LIKE '%BHVCOTO' THEN ROUND( d.`Số tiền thanh toán`/1.1, 0)
                when d.`Sản phẩm` = 'Trách nhiệm sản phẩm' then ROUND( d.`Số tiền thanh toán`/1.05, 0) 
            else ROUND(d.`Số tiền thanh toán`, 0) end as 'Doanh thu trước thuế',
            rate_bonus, exchange_core
        from detail d
        left join qd dsqd on dsqd.provider = d.`Đối tác nhà bảo hiểm` and upper(dsqd.product) = upper(d.`Sản phẩm`)
        ),
        t3 as (
        select t2.*, 
        case when date(`Ngày thanh toán`) = CURDATE() then `Số tiền thanh toán` end as `Doanh số hôm nay`,
        (rate_bonus*`Doanh thu trước thuế`) as EST_Bonus,
        (exchange_core*`Doanh thu trước thuế`) as `Doanh số qui đổi`
        from t2
        ),
        DSA as (
        select Code, `Họ tên`, `Chức danh`, Channel, `Thời gian bắt đầu`, `QUẢN LÝ CẤP 1 (BDM)`, `QUẢN LÝ CẤP 2 (BDD)`, sum(`Số tiền thanh toán`) as `Số tiền thanh toán`,
            sum(`Doanh số qui đổi`) as `Doanh số qui đổi`, sum(`Doanh thu trước thuế`) as `Doanh thu trước thuế`, sum(`Doanh số hôm nay`) as `Doanh số hôm nay`, sum(EST_Bonus) as EST_Bonus
        from t3 
        group by 1,2,3,4,5,6,7
        )
        ,

        t6 as (
        select dnsa.Code, dnsa.`Họ tên`, dnsa.`Chức danh`, dnsa.Channel, dnsa.`QUẢN LÝ CẤP 1 (BDM)`, dnsa.`QUẢN LÝ CẤP 2 (BDD)`, DSA.`Số tiền thanh toán`, DSA.`Doanh số qui đổi`, DSA.`Doanh thu trước thuế`,DSA.`Doanh số hôm nay`, DSA.`EST_Bonus`
        from ds_nhan_su_affina dnsa 
        left join DSA  
            ON TRIM(DSA.`Họ tên`) = TRIM(dnsa.`Họ tên`)
        AND TRIM(DSA.Code) = TRIM(dnsa.Code)
        where (dnsa.`Chức danh` in ('DSA', 'Agency', 'BDM_DV'))  and (dnsa.`QUẢN LÝ CẤP 2 (BDD)` in ('TRẦN THỊ THÙY AN','NGUYỄN THỊ HỒNG LOAN','BÙI THỊ THỦY TIÊN' ))
        )
        ,
        -- Tracking BDM_core
        t7 as (
        select 
        dnsa.Code, dnsa.`Họ tên`, dnsa.`Chức danh`, date(dnsa.`Thời gian bắt đầu`) as `Thời gian bắt đầu`, dnsa.`QUẢN LÝ CẤP 2 (BDD)`, sum(`Số tiền thanh toán`) as `Số tiền thanh toán`, coalesce(sum(`Doanh thu trước thuế`),0) as `Doanh thu trước thuế`, sum(`Doanh số qui đổi`) as `Doanh số qui đổi`, sum(EST_Bonus) as EST_Bonus,
        sum(`Doanh số hôm nay`) as `Doanh số hôm nay`
        from ds_nhan_su_affina dnsa
        left join DSA f on cast(f.`QUẢN LÝ CẤP 1 (BDM)` as binary) = cast(dnsa.`Họ tên` as binary)
        where (upper(dnsa.`Chức danh`)) like '%BDM%' 
        group by 1,2,3,4,5 
        ),
        t8 as (
        select t7.*,
            10 as `KPI tuyển dụng mới`,
            20 as `KPI DSA Active`,
            165000000 as `KPI Phí bảo hiểm qui đổi`,
            count(distinct case when dnsa.Status in ('A', 'P') and dnsa.`Chức danh` in ('DSA', 'Agency') then dnsa.Code end) as `Số DSA thực tế`,
            count(distinct case when dnsa.Status in ('A', 'P') and dnsa.`Chức danh` in ('DSA', 'Agency') and cast(dnsa.`Thời gian bắt đầu` as date) between '2025-02-01' and '2025-02-28' then dnsa.Code end) as `Tuyển dụng mới DSA`,
            count(distinct case when d.`Chức danh` not like '%BDM%' then d.Code end) as 'DSA Active'
        from t7
        join ds_nhan_su_affina dnsa on cast(dnsa.`QUẢN LÝ CẤP 1 (BDM)` as binary) = cast(t7.`Họ tên` as binary)
        left join DSA d on d.`QUẢN LÝ CẤP 1 (BDM)` = t7.`Họ tên`
        group by 1,2,3,4,5,6,7,8,9,10
        )
        ,
        BDM as (
        SELECT 
            a.*,
            round(`Doanh số qui đổi` / `KPI Phí bảo hiểm qui đổi`,2) AS `%_KPI doanh số qui đổi`,
            ROUND(
            LEAST(1.0, 
                (IF(`Tuyển dụng mới DSA` >= 10, 0.2, `Tuyển dụng mới DSA` * 0.2 / `KPI tuyển dụng mới`)) + 
                (CASE WHEN `DSA Active` >= 20 THEN 0.2 ELSE `DSA Active` * 0.2 / `KPI DSA Active` END) + 
                (IF(`Doanh số qui đổi` >= 165000000, 0.6, `Doanh số qui đổi` * 0.6 / 165000000))
            ), 2
            ) AS `%_KPI tổng`,
            b.`Tổng số tiền thanh toán tháng trước`,
            c.`Số tiền thanh toán cùng kì`
        FROM t8 AS a
        LEFT JOIN (
            SELECT 
                `QUẢN LÝ CẤP 1 (BDM)`, 
                SUM(`Số tiền thanh toán`) AS `Tổng số tiền thanh toán tháng trước`
            FROM t1
            WHERE 
                YEAR(`Ngày thanh toán`) = YEAR(NOW()) 
                AND MONTH(`Ngày thanh toán`) = MONTH(NOW()) - 1
            GROUP BY `QUẢN LÝ CẤP 1 (BDM)`
        ) AS b 
        ON b.`QUẢN LÝ CẤP 1 (BDM)` = a.`Họ tên`

        left join (
        SELECT `QUẢN LÝ CẤP 1 (BDM)`, SUM(`Số tiền thanh toán`) AS `Số tiền thanh toán cùng kì` FROM t1
        WHERE YEAR(`Ngày thanh toán`) = YEAR(NOW()) AND MONTH(`Ngày thanh toán`) = MONTH(NOW()) - 1 and day(`Ngày thanh toán`) <= day(now())
        GROUP BY `QUẢN LÝ CẤP 1 (BDM)`
        ) as c
        ON c.`QUẢN LÝ CẤP 1 (BDM)` = a.`Họ tên`
        ),
        nearly_BDD1 as (
        select `QUẢN LÝ CẤP 2 (BDD)`, sum(`Số tiền thanh toán`) as `Số tiền thanh toán`, sum(`Doanh số qui đổi`) as `Doanh số qui đổi`, sum(`Doanh thu trước thuế`) as `Doanh thu trước thuế`,
        sum(`EST_Bonus`) as `EST_Bonus`
        from DSA
        where `QUẢN LÝ CẤP 2 (BDD)` in ('BÙI THỊ THỦY TIÊN','TRẦN THỊ THÙY AN','NGUYỄN THỊ HỒNG LOAN'  )
        group by 1
        ), 
        nearly_BDD2 as (
        SELECT 
            a.*,
            b.`Tổng số tiền thanh toán tháng trước`,
            c.`Số tiền thanh toán cùng kì`,
            d.`Tuyển dụng mới DSA`, d.`Số DSA thực tế`, d.`DSA Active`, d.`KPI tuyển dụng mới`, d.`KPI DSA Active`, d.`KPI Phí bảo hiểm qui đổi`
        FROM nearly_BDD1 AS a
        LEFT JOIN (
            SELECT 
                `QUẢN LÝ CẤP 2 (BDD)`, 
                SUM(`Số tiền thanh toán`) AS `Tổng số tiền thanh toán tháng trước`
            FROM t1
            WHERE 
                YEAR(`Ngày thanh toán`) = YEAR(NOW()) 
                AND MONTH(`Ngày thanh toán`) = MONTH(NOW()) - 1
            GROUP BY `QUẢN LÝ CẤP 2 (BDD)`
        ) AS b 
        ON b.`QUẢN LÝ CẤP 2 (BDD)` = a.`QUẢN LÝ CẤP 2 (BDD)`

        left join (
        SELECT `QUẢN LÝ CẤP 2 (BDD)`, SUM(`Số tiền thanh toán`) AS `Số tiền thanh toán cùng kì` FROM t1
        WHERE YEAR(`Ngày thanh toán`) = YEAR(NOW()) AND MONTH(`Ngày thanh toán`) = MONTH(NOW()) - 1 and day(`Ngày thanh toán`) <= day(now())
        GROUP BY `QUẢN LÝ CẤP 2 (BDD)`
        ) as c
        ON c.`QUẢN LÝ CẤP 2 (BDD)` = a.`QUẢN LÝ CẤP 2 (BDD)`

        join (
        select 
        `QUẢN LÝ CẤP 2 (BDD)`, sum(`Tuyển dụng mới DSA`) as `Tuyển dụng mới DSA`, sum(`Số DSA thực tế`) as `Số DSA thực tế`, sum(`DSA Active`) as `DSA Active`,
        50 AS `KPI tuyển dụng mới`, 
        100 AS `KPI DSA Active`,
        825000000 AS `KPI Phí bảo hiểm qui đổi`
        from BDM
        group by 1
        ) as d on d.`QUẢN LÝ CẤP 2 (BDD)` = a.`QUẢN LÝ CẤP 2 (BDD)`
        )
        select 
        nearly_BDD2.*,
            LEAST(1.0, 
                (IF(`Tuyển dụng mới DSA` >= 50, 0.2, `Tuyển dụng mới DSA` * 0.2 / `KPI tuyển dụng mới`)) + 
                (CASE WHEN `DSA Active` >= 100 THEN 0.2 ELSE `DSA Active` * 0.2 / `KPI DSA Active` END) + 
                (IF(`Doanh số qui đổi` >= 825000000, 0.6, `Doanh số qui đổi` * 0.6 / 825000000))
            ) AS `%_KPI tổng`
        from nearly_BDD2
        """
        cursor.execute(detail)  
        tables = cursor.fetchall()
        numeric_cols = ["Số tiền thanh toán", "Doanh thu trước thuế", "Doanh số qui đổi", "EST_Bonus"]
        columns = [col[0] for col in cursor.description]
        df = pd.DataFrame(tables, columns=columns)
        show_grid(df,numeric_cols )



