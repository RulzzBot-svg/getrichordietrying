import { useNavigate } from "react-router-dom";

export default function LogoutButton() {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("tech");
    navigate("/");
  };

  return (
    <button className="btn btn-ghost btn-sm w-full text-error" onClick={handleLogout}>
      🚪 Logout
    </button>
  );
}
