import "./globals.css";

export const metadata = {
  title: "Municipal Control Room",
  description: "AI-Powered Street Safety Device Network"
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>
        <div className="app-shell">{children}</div>
      </body>
    </html>
  );
}
