import {
  useClerk as useClerkReal,
  useUser as useUserReal,
  Show as ShowReal
} from "@clerk/react";
import React from "react";
import { useLocation } from "wouter";

export const isMockAuth = !import.meta.env.VITE_CLERK_PUBLISHABLE_KEY ||
  import.meta.env.VITE_CLERK_PUBLISHABLE_KEY.includes("your_clerk") ||
  import.meta.env.VITE_CLERK_PUBLISHABLE_KEY.includes("mock");

export function useUser() {
  if (isMockAuth) {
    return {
      user: {
        id: "mock-user-123",
        imageUrl: "",
        fullName: "Local Developer",
        primaryEmailAddress: { emailAddress: "developer@localhost" },
      },
      isLoaded: true,
      isSignedIn: true,
    };
  }
  return useUserReal();
}

export function useClerk() {
  const [, setLocation] = useLocation();
  if (isMockAuth) {
    const basePath = import.meta.env.BASE_URL.replace(/\/$/, "");
    return {
      signOut: async () => {
        setLocation("/");
      },
      addListener: () => () => {},
    };
  }
  return useClerkReal();
}

export function Show({ when, children }: { when: "signed-in" | "signed-out"; children: React.ReactNode }) {
  if (isMockAuth) {
    if (when === "signed-in") return React.createElement(React.Fragment, null, children);
    return null;
  }
  return React.createElement(ShowReal, { when }, children);
}
