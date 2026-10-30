using System;
using System.Collections.Generic;
using System.Text;
using Domain.Enums;
using System.ComponentModel.DataAnnotations;

namespace Domain.Entities
{
    public class DashboardAccount
    {
        [Key]
        public int Id { get; set; }

        [Required]
        public string FullName { get; set; }

        [EmailAddress]
        [Required]
        public string Email { get; set; }

        [Required]
        public string PasswordHash { get; set; }

        public Role Role { get; set; }


        public bool IsActive { get; set; } = true;

    }
}
