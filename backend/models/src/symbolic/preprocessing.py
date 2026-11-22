import ipaddress
#Chuẩn hóa URL đầu vào trước khi phân tích
def _normalise_url(url: str) -> str:
    #Chuyển đầu vào thành chuỗi và loại bỏ khoảng trắng ở hai đầu
    value = str(url or "").strip()

    #Trả về chuỗi rỗng nếu URL không có dữ liệu
    if not value:
        return ""

    #Bổ sung giao thức HTTP nếu URL chưa khai báo giao thức
    if "://" not in value:
        value = "http://" + value

    return value


#Kiểm tra hostname có phải là địa chỉ IPv4 hoặc IPv6 hay không
def _is_ip(host: str) -> bool:
    try:
        #Loại bỏ dấu ngoặc vuông của địa chỉ IPv6 trước khi kiểm tra
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        #Trả về False nếu hostname không phải địa chỉ IP hợp lệ
        return False


#Trích xuất domain đăng ký gần đúng từ hostname
def _registered_domain(host: str) -> str:
    #Chuyển hostname về chữ thường, loại bỏ dấu chấm ở hai đầu và tách thành các thành phần
    parts = [p for p in host.lower().strip(".").split(".") if p]

    #Nếu hostname có tối đa hai thành phần thì trả về toàn bộ hostname
    if len(parts) <= 2:
        return ".".join(parts)

    #Các hậu tố phổ biến có cấu trúc gồm hai cấp, chẳng hạn co.uk hoặc com.vn
    common_second_level = {
        "co.uk", "org.uk", "ac.uk", "com.au", "net.au", "org.au",
        "co.jp", "co.nz", "com.br", "com.cn", "com.sg", "com.vn",
    }

    #Lấy hai thành phần cuối của hostname để kiểm tra hậu tố domain
    last_two = ".".join(parts[-2:])

    #Nếu thuộc nhóm hậu tố hai cấp thì lấy thêm một thành phần phía trước
    if last_two in common_second_level and len(parts) >= 3:
        return ".".join(parts[-3:])

    #Mặc định lấy hai thành phần cuối làm domain đăng ký gần đúng
    return ".".join(parts[-2:])