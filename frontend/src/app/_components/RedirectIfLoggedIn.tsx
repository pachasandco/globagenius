"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function RedirectIfLoggedIn() {
  const router = useRouter();
  useEffect(() => {
    const userId = localStorage.getItem("gg_user_id");
    const token = localStorage.getItem("gg_token");
    if (userId && token) {
      router.replace("/home");
    }
  }, [router]);
  return null;
}
